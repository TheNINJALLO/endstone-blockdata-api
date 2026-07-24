#include "endstone_blockdata/nbt.h"
#include <sstream>

namespace endstone_blockdata {
namespace {
void mix(std::uint64_t &h, std::uint64_t v) { h ^= v + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2); }
std::uint64_t hs(const std::string &s) { return std::hash<std::string>{}(s); }
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
