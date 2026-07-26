#pragma once
#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <variant>
#include <vector>

namespace endstone_blockdata {
struct NbtValue;
using NbtList = std::vector<NbtValue>;
using NbtCompound = std::map<std::string, NbtValue>;
using ByteArray = std::vector<std::int8_t>;
using IntArray = std::vector<std::int32_t>;
using LongArray = std::vector<std::int64_t>;

struct NbtValue {
    using ListPtr = std::shared_ptr<NbtList>;
    using CompoundPtr = std::shared_ptr<NbtCompound>;
    using Value = std::variant<std::monostate, bool, std::int8_t, std::int16_t, std::int32_t,
        std::int64_t, float, double, std::string, ByteArray, IntArray, LongArray, ListPtr, CompoundPtr>;
    Value value;

    NbtValue() = default;
    NbtValue(const NbtValue &other);
    NbtValue &operator=(const NbtValue &other);
    NbtValue(NbtValue &&) noexcept = default;
    NbtValue &operator=(NbtValue &&) noexcept = default;
    template <typename T> NbtValue(T v) : value(std::move(v)) {}
    static NbtValue list(NbtList values);
    static NbtValue compound(NbtCompound values);
};

std::uint64_t hashNbt(const NbtValue &value);
[[nodiscard]] bool nbtEqual(const NbtValue &left, const NbtValue &right);
// Validates values before conversion to a native NBT tree. End/null is a list
// terminator rather than a payload value, and NBT lists must have one tag type.
[[nodiscard]] bool validateNbtPayload(const NbtValue &value, std::string *error = nullptr);
std::string debugNbt(const NbtValue &value);
}
