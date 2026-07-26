#include "endstone_blockdata/nbt.h"
#include <optional>
#include <sstream>
#include <type_traits>
#include <unordered_set>
#include <utility>

namespace endstone_blockdata {
namespace {
void mix(std::uint64_t &h, std::uint64_t v) { h ^= v + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2); }
std::uint64_t hs(const std::string &s) { return std::hash<std::string>{}(s); }
NbtValue::Value cloneValue(const NbtValue::Value &value) {
    return std::visit([](const auto &entry) -> NbtValue::Value {
        using T = std::decay_t<decltype(entry)>;
        if constexpr (std::is_same_v<T, NbtValue::ListPtr>) {
            return entry ? std::make_shared<NbtList>(*entry) : NbtValue::ListPtr{};
        } else if constexpr (std::is_same_v<T, NbtValue::CompoundPtr>) {
            return entry ? std::make_shared<NbtCompound>(*entry) : NbtValue::CompoundPtr{};
        } else {
            return entry;
        }
    }, value);
}

enum class NbtPayloadType {
    End,
    Byte,
    Short,
    Int,
    Long,
    Float,
    Double,
    String,
    ByteArray,
    IntArray,
    LongArray,
    List,
    Compound,
};

NbtPayloadType payloadType(const NbtValue &value) {
    return std::visit([](const auto &entry) {
        using T = std::decay_t<decltype(entry)>;
        if constexpr (std::is_same_v<T, std::monostate>) return NbtPayloadType::End;
        else if constexpr (std::is_same_v<T, bool> || std::is_same_v<T, std::int8_t>) return NbtPayloadType::Byte;
        else if constexpr (std::is_same_v<T, std::int16_t>) return NbtPayloadType::Short;
        else if constexpr (std::is_same_v<T, std::int32_t>) return NbtPayloadType::Int;
        else if constexpr (std::is_same_v<T, std::int64_t>) return NbtPayloadType::Long;
        else if constexpr (std::is_same_v<T, float>) return NbtPayloadType::Float;
        else if constexpr (std::is_same_v<T, double>) return NbtPayloadType::Double;
        else if constexpr (std::is_same_v<T, std::string>) return NbtPayloadType::String;
        else if constexpr (std::is_same_v<T, ByteArray>) return NbtPayloadType::ByteArray;
        else if constexpr (std::is_same_v<T, IntArray>) return NbtPayloadType::IntArray;
        else if constexpr (std::is_same_v<T, LongArray>) return NbtPayloadType::LongArray;
        else if constexpr (std::is_same_v<T, NbtValue::ListPtr>) return NbtPayloadType::List;
        else return NbtPayloadType::Compound;
    }, value.value);
}

bool validationFailure(std::string *error, std::string message) {
    if (error) *error = std::move(message);
    return false;
}

bool validateNbtPayloadImpl(const NbtValue &value, const std::string &path, std::size_t depth,
                            std::unordered_set<const void *> &active, std::string *error) {
    if (depth > 64)
        return validationFailure(error, path + " exceeds the maximum NBT nesting depth of 64");
    const auto type = payloadType(value);
    if (type == NbtPayloadType::End)
        return validationFailure(error, path + " contains an End/null value; remove the field instead");

    if (const auto *list = std::get_if<NbtValue::ListPtr>(&value.value)) {
        if (!*list)
            return validationFailure(error, path + " contains a null NBT list pointer");
        const auto *identity = static_cast<const void *>(list->get());
        if (!active.insert(identity).second)
            return validationFailure(error, path + " contains a cyclic NBT list");

        std::optional<NbtPayloadType> element_type;
        for (std::size_t index = 0; index < (*list)->size(); ++index) {
            const auto &entry = (**list)[index];
            const auto entry_path = path + "[" + std::to_string(index) + "]";
            if (!validateNbtPayloadImpl(entry, entry_path, depth + 1, active, error)) {
                active.erase(identity);
                return false;
            }
            const auto current_type = payloadType(entry);
            if (element_type && *element_type != current_type) {
                active.erase(identity);
                return validationFailure(error, path + " must contain one NBT tag type; element " +
                                                std::to_string(index) + " differs");
            }
            element_type = current_type;
        }
        active.erase(identity);
    } else if (const auto *compound = std::get_if<NbtValue::CompoundPtr>(&value.value)) {
        if (!*compound)
            return validationFailure(error, path + " contains a null NBT compound pointer");
        const auto *identity = static_cast<const void *>(compound->get());
        if (!active.insert(identity).second)
            return validationFailure(error, path + " contains a cyclic NBT compound");
        for (const auto &[key, entry] : **compound) {
            if (!validateNbtPayloadImpl(entry, path + "." + key, depth + 1, active, error)) {
                active.erase(identity);
                return false;
            }
        }
        active.erase(identity);
    }
    return true;
}
}
NbtValue::NbtValue(const NbtValue &other) : value(cloneValue(other.value)) {}
NbtValue &NbtValue::operator=(const NbtValue &other) {
    if (this != &other) value = cloneValue(other.value);
    return *this;
}
NbtValue NbtValue::list(NbtList values) { return NbtValue{std::make_shared<NbtList>(std::move(values))}; }
NbtValue NbtValue::compound(NbtCompound values) { return NbtValue{std::make_shared<NbtCompound>(std::move(values))}; }

std::uint64_t hashNbt(const NbtValue &v) {
    std::uint64_t h = v.value.index() + 1469598103934665603ULL;
    std::visit([&](const auto &x) {
        using T = std::decay_t<decltype(x)>;
        if constexpr (std::is_same_v<T, std::monostate>) {}
        else if constexpr (std::is_arithmetic_v<T>) mix(h, std::hash<T>{}(x));
        else if constexpr (std::is_same_v<T, std::string>) mix(h, hs(x));
        else if constexpr (std::is_same_v<T, ByteArray> || std::is_same_v<T, IntArray> || std::is_same_v<T, LongArray>) {
            for (auto n : x) mix(h, std::hash<decltype(n)>{}(n));
        } else if constexpr (std::is_same_v<T, NbtValue::ListPtr>) {
            if (x) for (const auto &e : *x) mix(h, hashNbt(e));
        } else if constexpr (std::is_same_v<T, NbtValue::CompoundPtr>) {
            if (x) for (const auto &[k,e] : *x) { mix(h, hs(k)); mix(h, hashNbt(e)); }
        }
    }, v.value);
    return h;
}

bool nbtEqual(const NbtValue &left, const NbtValue &right) {
    if (left.value.index() != right.value.index()) return false;
    return std::visit([&](const auto &a) -> bool {
        using T = std::decay_t<decltype(a)>;
        const auto *b = std::get_if<T>(&right.value);
        if (!b) return false;
        if constexpr (std::is_same_v<T, NbtValue::ListPtr>) {
            if (static_cast<bool>(a) != static_cast<bool>(*b)) return false;
            if (!a) return true;
            if (a->size() != (*b)->size()) return false;
            for (std::size_t i = 0; i < a->size(); ++i) if (!nbtEqual((*a)[i], (**b)[i])) return false;
            return true;
        } else if constexpr (std::is_same_v<T, NbtValue::CompoundPtr>) {
            if (static_cast<bool>(a) != static_cast<bool>(*b)) return false;
            if (!a) return true;
            if (a->size() != (*b)->size()) return false;
            for (const auto &[key, value] : *a) {
                auto it = (*b)->find(key);
                if (it == (*b)->end() || !nbtEqual(value, it->second)) return false;
            }
            return true;
        } else {
            return a == *b;
        }
    }, left.value);
}

bool validateNbtPayload(const NbtValue &value, std::string *error) {
    if (error) error->clear();
    std::unordered_set<const void *> active;
    return validateNbtPayloadImpl(value, "$", 0, active, error);
}

std::string debugNbt(const NbtValue &v) {
    return std::visit([](const auto &x) -> std::string {
        using T = std::decay_t<decltype(x)>;
        if constexpr (std::is_same_v<T, std::monostate>) return "null";
        else if constexpr (std::is_same_v<T, bool>) return x ? "true" : "false";
        else if constexpr (std::is_arithmetic_v<T>) return std::to_string(x);
        else if constexpr (std::is_same_v<T, std::string>) return "\"" + x + "\"";
        else if constexpr (std::is_same_v<T, NbtValue::ListPtr>) {
            std::string out="["; if (x) for (size_t i=0;i<x->size();++i) { if(i) out+=","; out+=debugNbt((*x)[i]); } return out+"]";
        } else if constexpr (std::is_same_v<T, NbtValue::CompoundPtr>) {
            std::string out="{"; bool first=true; if(x) for(const auto &[k,e]:*x){ if(!first) out+=","; first=false; out+=k+":"+debugNbt(e);} return out+"}";
        } else return "<array:" + std::to_string(x.size()) + ">";
    }, v.value);
}
}
