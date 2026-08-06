from conan import ConanFile
from conan.tools.cmake import CMakeDeps, CMakeToolchain


class ExactEndstoneDependencies(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    options = {"bds_build": ["1.26.40"]}
    default_options = {
        "bds_build": "1.26.40",
        "boost/*:header_only": True,
        "date/*:header_only": True,
        "raknet/*:minecraft_version": "r26u3",
    }

    def requirements(self):
        # These must match the exact Endstone tag selected in CMake. Private
        # Bedrock layouts are not a semver-stable dependency surface.
        self.requires("base64/0.5.2")
        self.requires("concurrentqueue/1.0.4")
        self.requires("cpptrace/1.0.4")
        self.requires("date/3.0.4")
        self.requires("funchook/1.1.3")
        self.requires("magic_enum/0.9.7")
        self.requires("nlohmann_json/3.12.0")
        self.requires("pybind11/3.0.1")
        self.requires("raknet/4.081-mojang")
        self.requires("replxx/0.0.4")
        self.requires("tomlplusplus/3.3.0")
        self.requires("zstr/1.0.7")

        # Endstone v0.11.7 exact dependency graph.
        self.requires("boost/1.91.0")
        self.requires("entt/3.16.0")
        self.requires("expected-lite/0.9.0")
        self.requires("glm/1.0.3")
        self.requires("ms-gsl/4.2.2")
        self.requires("sentry-native/0.14.2")
        self.requires("spdlog/1.17.0", options={"use_std_fmt": True})

        if self.settings.os == "Windows":
            self.requires("detours/cci.20220630")
        elif self.settings.os == "Linux":
            self.requires("libelf/0.8.13")

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["ENDSTONE_CONAN_BDS_BUILD"] = str(self.options.bds_build)
        tc.preprocessor_definitions["ENTT_SPARSE_PAGE"] = 2048
        tc.preprocessor_definitions["ENTT_NO_MIXIN"] = "1"
        tc.generate()
