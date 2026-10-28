// Generated offline BDS 1.26.60.6 preparation; never a qualified runtime profile.
#pragma once
#include <cstdint>
#include <optional>
namespace endstone_blockdata::prepared::bds_1_26_60 {
inline constexpr bool RuntimeQualified = false;
inline constexpr bool ReleaseReady = false;
inline constexpr const char* PackageVersion = "1.26.60.6";
namespace Linux {
struct BdsOffsets {
    static constexpr std::optional<std::uintptr_t> CreateTrackerRva = std::uintptr_t{0xbc50800ULL};
    static constexpr std::optional<std::uintptr_t> FlattenStorageItemCoreRva = std::uintptr_t{0xc4afac1ULL};
    static constexpr std::optional<std::uintptr_t> FlattenStorageItemRva = std::uintptr_t{0xc4afa50ULL};
    static constexpr std::optional<std::uintptr_t> ManagerGiveLifetimeRva = std::uintptr_t{0xbc2b970ULL};
    static constexpr std::optional<std::uintptr_t> ReceiveContainerLifetimesRva = std::uintptr_t{0xb540220ULL};
    static constexpr std::optional<std::uintptr_t> TrackStorageItemRva = std::uintptr_t{0xbc4f1d0ULL};
};
} // namespace Linux
} // namespace endstone_blockdata::prepared::bds_1_26_60
