#pragma once
#include <cstdint>
#include <optional>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

namespace endstone_blockdata {
using BlockStateValue = std::variant<bool, std::int32_t, std::string>;
using BlockStates = std::unordered_map<std::string, BlockStateValue>;

struct BlockLocation {
    std::string dimension{"overworld"};
    std::int32_t x{};
    std::int32_t y{};
    std::int32_t z{};
    auto operator<=>(const BlockLocation &) const = default;
};

struct BlockRegion {
    BlockLocation minimum;
    BlockLocation maximum;
};

enum class ConflictPolicy {
    FailIfChanged,
    MergeChangedPaths,
    MergeInventorySlots,
    Replace,
    Force
};

enum class ApplyStatus {
    Applied,
    Conflict,
    ChunkUnavailable,
    Unsupported,
    InvalidPatch,
    AdapterError
};

struct ApplyResult {
    ApplyStatus status{ApplyStatus::AdapterError};
    std::string message;
    std::uint64_t resulting_revision{};
    [[nodiscard]] bool ok() const noexcept { return status == ApplyStatus::Applied; }
};
}
