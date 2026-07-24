#include "endstone_blockdata/live_service.h"
#include "endstone_blockdata/nbt.h"
#include <endstone/endstone.hpp>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>
#include <variant>

namespace py = pybind11;
using namespace endstone_blockdata;

namespace {
py::object nbtToPython(const NbtValue &value) {
    return std::visit([](const auto &v) -> py::object {
        using T = std::decay_t<decltype(v)>;
        if constexpr (std::is_same_v<T, std::monostate>) return py::none();
        else if constexpr (std::is_same_v<T, bool>) return py::bool_(v);
        else if constexpr (std::is_arithmetic_v<T>) return py::cast(v);
        else if constexpr (std::is_same_v<T, std::string>) return py::str(v);
        else if constexpr (std::is_same_v<T, ByteArray> || std::is_same_v<T, IntArray> ||
                           std::is_same_v<T, LongArray>) return py::cast(v);
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
}
