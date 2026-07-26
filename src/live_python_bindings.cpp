#include "endstone_blockdata/live_service.h"
#include "endstone_blockdata/nbt.h"
#include <endstone/endstone.hpp>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

namespace py = pybind11;
using namespace endstone_blockdata;

namespace {
constexpr std::size_t MaxPythonNbtDepth = 64;
constexpr std::int64_t MaxLiveRegionBlocks = 32768;
constexpr const char *NbtArrayMarker = "__endstone_nbt_array__";

template <typename T>
py::dict nbtArrayToPython(const char *kind, const std::vector<T> &array) {
    py::list values;
    for (const auto entry : array)
        values.append(py::cast(static_cast<std::int64_t>(entry)));
    py::dict out;
    out[py::str(NbtArrayMarker)] = py::str(kind);
    out[py::str("values")] = std::move(values);
    return out;
}

py::object nbtToPython(const NbtValue &value) {
    return std::visit([](const auto &v) -> py::object {
        using T = std::decay_t<decltype(v)>;
        if constexpr (std::is_same_v<T, std::monostate>)
            throw std::runtime_error("NBT End/null cannot be exposed as a payload value");
        else if constexpr (std::is_same_v<T, bool>) return py::bool_(v);
        else if constexpr (std::is_arithmetic_v<T>) return py::cast(v);
        else if constexpr (std::is_same_v<T, std::string>) return py::str(v);
        else if constexpr (std::is_same_v<T, ByteArray>) return nbtArrayToPython("byte", v);
        else if constexpr (std::is_same_v<T, IntArray>) return nbtArrayToPython("int", v);
        else if constexpr (std::is_same_v<T, LongArray>) return nbtArrayToPython("long", v);
        else if constexpr (std::is_same_v<T, NbtValue::ListPtr>) {
            py::list out;
            if (v) for (const auto &entry : *v) out.append(nbtToPython(entry));
            return std::move(out);
        } else if constexpr (std::is_same_v<T, NbtValue::CompoundPtr>) {
            py::dict out;
            if (v) for (const auto &[key, entry] : *v) out[py::str(key)] = nbtToPython(entry);
            return std::move(out);
        }
    }, value.value);
}

std::int64_t checkedNbtInteger(py::handle value, const std::string &context) {
    if (py::isinstance<py::bool_>(value) || !py::isinstance<py::int_>(value))
        throw py::type_error(context + " must be an integer, not bool");
    const auto number = PyLong_AsLongLong(value.ptr());
    if (number == -1 && PyErr_Occurred()) {
        PyErr_Clear();
        throw py::value_error(context + " must fit in signed 64 bits");
    }
    return static_cast<std::int64_t>(number);
}

template <typename T>
std::vector<T> nbtArrayFromPython(const py::sequence &values, const char *kind) {
    std::vector<T> out;
    out.reserve(static_cast<std::size_t>(py::len(values)));
    std::size_t index = 0;
    for (const auto &entry : values) {
        const auto context = std::string("NBT ") + kind + " array value at index " + std::to_string(index);
        const auto number = checkedNbtInteger(entry, context);
        if (number < static_cast<std::int64_t>(std::numeric_limits<T>::min()) ||
            number > static_cast<std::int64_t>(std::numeric_limits<T>::max())) {
            throw py::value_error(context + " is outside the signed " +
                                  std::to_string(sizeof(T) * 8) + "-bit range");
        }
        out.push_back(static_cast<T>(number));
        ++index;
    }
    return out;
}

NbtValue typedNbtArrayFromPython(const py::dict &wrapper) {
    if (wrapper.size() != 2 || !wrapper.contains(py::str("values")))
        throw py::value_error(std::string("NBT array wrapper must contain only '") +
                              NbtArrayMarker + "' and 'values'");
    const auto marker = py::reinterpret_borrow<py::object>(wrapper[py::str(NbtArrayMarker)]);
    if (!py::isinstance<py::str>(marker))
        throw py::type_error(std::string("NBT array wrapper '") + NbtArrayMarker + "' must be a string");
    const auto values = py::reinterpret_borrow<py::object>(wrapper[py::str("values")]);
    if (!py::isinstance<py::list>(values) && !py::isinstance<py::tuple>(values))
        throw py::type_error("NBT array wrapper 'values' must be a list or tuple");

    const auto sequence = py::reinterpret_borrow<py::sequence>(values);
    const auto kind = py::cast<std::string>(marker);
    if (kind == "byte") return nbtArrayFromPython<std::int8_t>(sequence, "byte");
    if (kind == "int") return nbtArrayFromPython<std::int32_t>(sequence, "int");
    if (kind == "long") return nbtArrayFromPython<std::int64_t>(sequence, "long");
    throw py::value_error("NBT array wrapper type must be 'byte', 'int', or 'long'");
}

void requireValidNbtPayload(const NbtValue &value) {
    std::string error;
    if (!validateNbtPayload(value, &error)) throw py::value_error("invalid NBT payload: " + error);
}

NbtValue nbtFromPython(py::handle value, std::size_t depth = 0) {
    if (depth > MaxPythonNbtDepth)
        throw py::value_error("NBT nesting exceeds 64 levels");
    if (value.is_none())
        throw py::type_error("NBT None/null is not a payload value; remove the field instead");
    if (py::isinstance<py::bool_>(value)) return py::cast<bool>(value);
    if (py::isinstance<py::int_>(value)) {
        const auto number = checkedNbtInteger(value, "NBT integer");
        if (number >= std::numeric_limits<std::int32_t>::min() &&
            number <= std::numeric_limits<std::int32_t>::max()) {
            return static_cast<std::int32_t>(number);
        }
        return number;
    }
    if (py::isinstance<py::float_>(value)) return py::cast<double>(value);
    if (py::isinstance<py::str>(value)) return py::cast<std::string>(value);
    if (py::isinstance<py::bytes>(value) || py::isinstance<py::bytearray>(value)) {
        std::string bytes;
        if (py::isinstance<py::bytes>(value)) {
            bytes = py::cast<std::string>(value);
        } else {
            const auto size = PyByteArray_Size(value.ptr());
            auto *data = PyByteArray_AsString(value.ptr());
            if (size < 0 || !data) throw py::error_already_set();
            bytes.assign(data, static_cast<std::size_t>(size));
        }
        ByteArray out;
        out.reserve(bytes.size());
        for (const unsigned char byte : bytes) out.push_back(static_cast<std::int8_t>(byte));
        return out;
    }
    if (py::isinstance<py::dict>(value)) {
        const auto source = py::reinterpret_borrow<py::dict>(value);
        if (source.contains(py::str(NbtArrayMarker))) return typedNbtArrayFromPython(source);
        NbtCompound out;
        for (const auto &[key, entry] : source) {
            if (!py::isinstance<py::str>(key))
                throw py::type_error("NBT compound keys must be strings");
            out.emplace(py::cast<std::string>(key), nbtFromPython(entry, depth + 1));
        }
        auto result = NbtValue::compound(std::move(out));
        requireValidNbtPayload(result);
        return result;
    }
    if (py::isinstance<py::list>(value) || py::isinstance<py::tuple>(value)) {
        NbtList out;
        for (const auto &entry : py::reinterpret_borrow<py::sequence>(value))
            out.push_back(nbtFromPython(entry, depth + 1));
        auto result = NbtValue::list(std::move(out));
        requireValidNbtPayload(result);
        return result;
    }
    throw py::type_error("NBT values must be bool, int, float, str, bytes, list, tuple, dict, or a typed-array wrapper");
}

BlockStateValue stateFromPython(py::handle value) {
    if (py::isinstance<py::bool_>(value)) return py::cast<bool>(value);
    if (py::isinstance<py::int_>(value)) {
        const auto number = py::cast<std::int64_t>(value);
        if (number < std::numeric_limits<std::int32_t>::min() ||
            number > std::numeric_limits<std::int32_t>::max()) {
            throw py::value_error("block-state integers must fit in signed 32 bits");
        }
        return static_cast<std::int32_t>(number);
    }
    if (py::isinstance<py::str>(value)) return py::cast<std::string>(value);
    throw py::type_error("block-state values must be bool, int, or str");
}

py::object field(const py::dict &value, const char *name) {
    return py::reinterpret_borrow<py::object>(value[py::str(name)]);
}

void readStringSet(const py::dict &source, const char *name, std::set<std::string> &destination) {
    if (!source.contains(name)) return;
    const auto values = field(source, name);
    if (values.is_none()) return;
    if (py::isinstance<py::str>(values))
        throw py::type_error(std::string(name) + " must be an iterable of strings, not a string");
    for (const auto &entry : py::reinterpret_borrow<py::iterable>(values)) {
        if (!py::isinstance<py::str>(entry))
            throw py::type_error(std::string(name) + " entries must be strings");
        destination.insert(py::cast<std::string>(entry));
    }
}

void readSlotSet(const py::dict &source, const char *name, std::set<std::int32_t> &destination) {
    if (!source.contains(name)) return;
    const auto values = field(source, name);
    if (values.is_none()) return;
    for (const auto &entry : py::reinterpret_borrow<py::iterable>(values)) {
        const auto slot = py::cast<std::int32_t>(entry);
        if (slot < 0) throw py::value_error(std::string(name) + " entries must be non-negative");
        destination.insert(slot);
    }
}

BlockPatch patchFromPython(const py::dict &source) {
    if (!source.contains("location") || !py::isinstance<py::dict>(field(source, "location")))
        throw py::type_error("patch.location must be a dict");
    const auto location = py::cast<py::dict>(field(source, "location"));
    for (const auto *name : {"dimension", "x", "y", "z"}) {
        if (!location.contains(name)) throw py::key_error(std::string("patch.location.") + name);
    }

    BlockPatch patch;
    patch.location.dimension = py::cast<std::string>(field(location, "dimension"));
    patch.location.x = py::cast<std::int32_t>(field(location, "x"));
    patch.location.y = py::cast<std::int32_t>(field(location, "y"));
    patch.location.z = py::cast<std::int32_t>(field(location, "z"));
    if (patch.location.dimension.empty()) throw py::value_error("patch.location.dimension must not be empty");

    if (source.contains("expected_revision") && !field(source, "expected_revision").is_none())
        patch.expected_revision = py::cast<std::uint64_t>(field(source, "expected_revision"));
    if (source.contains("replacement_type") && !field(source, "replacement_type").is_none()) {
        patch.replacement_type = py::cast<std::string>(field(source, "replacement_type"));
        if (patch.replacement_type->empty()) throw py::value_error("replacement_type must not be empty");
    }

    if (source.contains("state_updates") && !field(source, "state_updates").is_none()) {
        if (!py::isinstance<py::dict>(field(source, "state_updates")))
            throw py::type_error("state_updates must be a dict");
        for (const auto &[key, value] : py::cast<py::dict>(field(source, "state_updates"))) {
            if (!py::isinstance<py::str>(key)) throw py::type_error("state_updates keys must be strings");
            patch.state_updates.emplace(py::cast<std::string>(key), stateFromPython(value));
        }
    }
    readStringSet(source, "state_removals", patch.state_removals);

    if (source.contains("nbt_updates") && !field(source, "nbt_updates").is_none()) {
        if (!py::isinstance<py::dict>(field(source, "nbt_updates")))
            throw py::type_error("nbt_updates must be a dict");
        for (const auto &[key, value] : py::cast<py::dict>(field(source, "nbt_updates"))) {
            if (!py::isinstance<py::str>(key)) throw py::type_error("nbt_updates keys must be strings");
            patch.nbt_updates.emplace(py::cast<std::string>(key), nbtFromPython(value));
        }
    }
    readStringSet(source, "nbt_removals", patch.nbt_removals);

    if (source.contains("inventory_updates") && !field(source, "inventory_updates").is_none()) {
        if (!py::isinstance<py::dict>(field(source, "inventory_updates")))
            throw py::type_error("inventory_updates must be a dict");
        for (const auto &[key, value] : py::cast<py::dict>(field(source, "inventory_updates"))) {
            const auto slot = py::cast<std::int32_t>(key);
            if (slot < 0) throw py::value_error("inventory_updates keys must be non-negative slots");
            patch.inventory_updates.emplace(slot, InventorySlotSnapshot{slot, nbtFromPython(value), 0});
        }
    }
    readSlotSet(source, "inventory_removals", patch.inventory_removals);
    return patch;
}

ConflictPolicy conflictPolicyFromPython(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        if (c == '-' || c == ' ') return '_';
        return static_cast<char>(std::tolower(c));
    });
    if (value == "fail_if_changed") return ConflictPolicy::FailIfChanged;
    if (value == "merge_changed_paths") return ConflictPolicy::MergeChangedPaths;
    if (value == "merge_inventory_slots") return ConflictPolicy::MergeInventorySlots;
    if (value == "replace") return ConflictPolicy::Replace;
    if (value == "force") return ConflictPolicy::Force;
    throw py::value_error("unknown conflict policy: " + value);
}

std::string_view applyStatusName(ApplyStatus status) {
    switch (status) {
    case ApplyStatus::Applied: return "applied";
    case ApplyStatus::Conflict: return "conflict";
    case ApplyStatus::ChunkUnavailable: return "chunk_unavailable";
    case ApplyStatus::Unsupported: return "unsupported";
    case ApplyStatus::InvalidPatch: return "invalid_patch";
    case ApplyStatus::AdapterError: return "adapter_error";
    }
    return "adapter_error";
}

py::dict applyResultToPython(const ApplyResult &result) {
    py::dict out;
    out["ok"] = result.ok();
    out["status"] = applyStatusName(result.status);
    out["message"] = result.message;
    out["resulting_revision"] = result.resulting_revision;
    return out;
}

std::int64_t checkedRegionVolume(std::int32_t min_x, std::int32_t min_y, std::int32_t min_z,
                                 std::int32_t max_x, std::int32_t max_y, std::int32_t max_z) {
    const auto extent = [](std::int32_t left, std::int32_t right) {
        return static_cast<std::int64_t>(std::max(left, right)) - std::min(left, right) + 1;
    };
    const auto x = extent(min_x, max_x);
    const auto y = extent(min_y, max_y);
    const auto z = extent(min_z, max_z);
    if (x > MaxLiveRegionBlocks || y > MaxLiveRegionBlocks || z > MaxLiveRegionBlocks ||
        x * y > MaxLiveRegionBlocks || x * y * z > MaxLiveRegionBlocks) {
        throw py::value_error("capture_region is limited to 32768 blocks per primary-thread call");
    }
    return x * y * z;
}

py::dict snapshotToPython(const BlockSnapshot &snapshot) {
    py::dict location;
    location["dimension"] = snapshot.location.dimension;
    location["x"] = snapshot.location.x;
    location["y"] = snapshot.location.y;
    location["z"] = snapshot.location.z;

    py::dict states;
    for (const auto &[key, value] : snapshot.states) {
        std::visit([&](const auto &v) { states[py::str(key)] = py::cast(v); }, value);
    }

    py::dict out;
    out["location"] = std::move(location);
    out["type"] = snapshot.type;
    out["runtime_id"] = snapshot.runtime_id;
    out["states"] = std::move(states);
    out["revision"] = snapshot.revision;

    if (!snapshot.block_entity) {
        out["block_entity"] = py::none();
        return out;
    }

    py::dict actor;
    actor["type"] = snapshot.block_entity->type;
    actor["nbt"] = nbtToPython(snapshot.block_entity->nbt);
    actor["snbt"] = snapshot.block_entity->raw_snbt;
    actor["canonical"] = snapshot.block_entity->canonical_nbt;
    py::list inventory;
    for (const auto &slot : snapshot.block_entity->inventory) {
        py::dict item;
        item["slot"] = slot.slot;
        item["item"] = nbtToPython(slot.item);
        item["revision"] = slot.revision;
        inventory.append(std::move(item));
    }
    actor["inventory"] = std::move(inventory);
    out["block_entity"] = std::move(actor);
    return out;
}

std::shared_ptr<LiveBlockDataService> loadService(endstone::Server &server) {
    return server.getServiceManager().load<LiveBlockDataService>(std::string(BlockDataServiceName));
}
} // namespace

PYBIND11_MODULE(_endstone_blockdata_live, module) {
    module.doc() = "Live Endstone BlockData service bridge for Python anti-grief plugins";

    module.def("available", [](endstone::Server &server) { return static_cast<bool>(loadService(server)); },
               py::arg("server"));

    module.def("capabilities", [](endstone::Server &server) {
        auto service = loadService(server);
        if (!service) throw std::runtime_error("endstone:blockdata service is not registered");
        const auto c = service->capabilities();
        py::dict out;
        out["adapter"] = service->adapterName();
        out["block_states"] = c.block_states;
        out["block_writes"] = c.block_writes;
        out["block_entity_nbt"] = c.block_entity_nbt;
        out["block_entity_nbt_write"] = c.block_entity_nbt_write;
        out["canonical_actor_nbt"] = c.canonical_actor_nbt;
        out["item_user_nbt"] = c.item_user_nbt;
        out["inventory"] = c.inventory;
        out["container_save_nbt"] = c.container_save_nbt;
        out["raw_block_entity_nbt"] = c.raw_block_entity_nbt;
        return out;
    }, py::arg("server"));

    module.def("capture", [](endstone::Server &server, const std::string &dimension,
                              int x, int y, int z) -> py::object {
        if (!server.isPrimaryThread())
            throw std::runtime_error("live BlockData capture must run on the Endstone primary thread");
        auto service = loadService(server);
        if (!service) throw std::runtime_error("endstone:blockdata service is not registered");
        auto snapshot = service->capture({dimension, x, y, z});
        if (!snapshot) return py::none();
        return snapshotToPython(*snapshot);
    }, py::arg("server"), py::arg("dimension"), py::arg("x"), py::arg("y"), py::arg("z"));

    module.def("capture_region", [](endstone::Server &server, const std::string &dimension,
                                      std::int32_t min_x, std::int32_t min_y, std::int32_t min_z,
                                      std::int32_t max_x, std::int32_t max_y, std::int32_t max_z) {
        if (!server.isPrimaryThread())
            throw std::runtime_error("live BlockData region capture must run on the Endstone primary thread");
        checkedRegionVolume(min_x, min_y, min_z, max_x, max_y, max_z);
        auto service = loadService(server);
        if (!service) throw std::runtime_error("endstone:blockdata service is not registered");
        auto snapshots = service->captureRegion({{dimension, min_x, min_y, min_z},
                                                 {dimension, max_x, max_y, max_z}});
        py::list out;
        for (const auto &snapshot : snapshots) out.append(snapshotToPython(snapshot));
        return out;
    }, py::arg("server"), py::arg("dimension"),
       py::arg("min_x"), py::arg("min_y"), py::arg("min_z"),
       py::arg("max_x"), py::arg("max_y"), py::arg("max_z"));

    module.def("apply", [](endstone::Server &server, const py::dict &patch,
                            const std::string &conflict_policy) {
        if (!server.isPrimaryThread())
            throw std::runtime_error("live BlockData apply must run on the Endstone primary thread");
        auto service = loadService(server);
        if (!service) throw std::runtime_error("endstone:blockdata service is not registered");
        return applyResultToPython(service->apply(patchFromPython(patch),
                                                  conflictPolicyFromPython(conflict_policy)));
    }, py::arg("server"), py::arg("patch"), py::arg("conflict_policy") = "fail_if_changed");
}
