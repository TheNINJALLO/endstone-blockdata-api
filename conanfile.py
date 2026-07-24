from conan import ConanFile
from conan.tools.cmake import CMakeDeps, CMakeToolchain


class ExactEndstoneDependencies(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    default_options = {
        "boost/*:header_only": True,
        "raknet/*:minecraft_version": "r26u3",
    }

    def requirements(self):
        # Match the private Bedrock-header dependency versions used by
        # Endstone v0.11.5 and v0.11.6.
        self.requires("base64/0.5.2")
        self.requires("boost/1.86.0")
        self.requires("date/3.0.3")
        self.requires("entt/3.15.0")
        self.requires("expected-lite/0.8.0")
        self.requires("fmt/11.2.0")
        self.requires("glm/1.0.1")
        self.requires("magic_enum/0.9.7")
        self.requires("ms-gsl/4.2.0")
        self.requires("nlohmann_json/3.11.3")
        self.requires("raknet/4.081-mojang")

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.preprocessor_definitions["ENTT_SPARSE_PAGE"] = 2048
        tc.preprocessor_definitions["ENTT_NO_MIXIN"] = "1"
        tc.generate()
