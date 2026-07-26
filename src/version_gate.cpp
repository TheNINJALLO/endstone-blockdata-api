#include "endstone_blockdata/bds_26_30_adapter.h"

namespace endstone_blockdata {
namespace {
std::string_view canonicalBdsBuild(std::string_view build) noexcept {
    // Endstone reports the BDS minor/patch pair (for example, "26.33"),
    // while release packaging uses the full Minecraft version ("1.26.33").
    if (build.starts_with("1.")) build.remove_prefix(2);
    return build;
}

bool isAsciiAlphaNumeric(char value) noexcept {
    return (value >= '0' && value <= '9') ||
           (value >= 'A' && value <= 'Z') ||
           (value >= 'a' && value <= 'z');
}

bool isValidIdentifierList(std::string_view value) noexcept {
    if (value.empty() || value.front() == '.' || value.back() == '.') return false;
    bool previous_dot = false;
    for (const char current : value) {
        if (current == '.') {
            if (previous_dot) return false;
            previous_dot = true;
            continue;
        }
        if (!isAsciiAlphaNumeric(current) && current != '-') return false;
        previous_dot = false;
    }
    return true;
}

bool isDecimal(std::string_view value) noexcept {
    if (value.empty()) return false;
    for (const char current : value) {
        if (current < '0' || current > '9') return false;
    }
    return true;
}

bool isSafeEndstoneSuffix(std::string_view suffix) noexcept {
    if (suffix.starts_with('+')) {
        suffix.remove_prefix(1);
        return isValidIdentifierList(suffix);
    }

    if (suffix.starts_with(".dev")) {
        suffix.remove_prefix(4);
        const auto metadata = suffix.find('+');
        const auto serial = suffix.substr(0, metadata);
        if (!isDecimal(serial)) return false;
        return metadata == std::string_view::npos ||
               isValidIdentifierList(suffix.substr(metadata + 1));
    }

    if (suffix.starts_with("-dev")) {
        suffix.remove_prefix(4);
        if (suffix.empty()) return true;
        if (suffix.starts_with('+')) {
            suffix.remove_prefix(1);
            return isValidIdentifierList(suffix);
        }
        if (!suffix.starts_with('.')) return false;
        suffix.remove_prefix(1);
        const auto metadata = suffix.find('+');
        const auto prerelease = suffix.substr(0, metadata);
        if (!isValidIdentifierList(prerelease)) return false;
        return metadata == std::string_view::npos ||
               isValidIdentifierList(suffix.substr(metadata + 1));
    }

    return false;
}
} // namespace

bool isSupportedBds2630Build(std::string_view build) noexcept {
    return canonicalBdsBuild(build) == "26.33";
}

bool isExpectedBds2630Build(std::string_view runtime_build,
                            std::string_view packaged_build) noexcept {
    if (!isSupportedBds2630Build(runtime_build) ||
        !isSupportedBds2630Build(packaged_build)) {
        return false;
    }
    return canonicalBdsBuild(runtime_build) == canonicalBdsBuild(packaged_build);
}

bool isExpectedEndstoneVersion(std::string_view runtime_version,
                               std::string_view packaged_version) noexcept {
    if (runtime_version.starts_with('v')) runtime_version.remove_prefix(1);
    if (packaged_version.starts_with('v')) packaged_version.remove_prefix(1);
    if (runtime_version.empty() || packaged_version.empty()) return false;
    if (runtime_version == packaged_version) return true;
    if (!runtime_version.starts_with(packaged_version)) return false;
    return isSafeEndstoneSuffix(runtime_version.substr(packaged_version.size()));
}
}
