# Exact build dependencies

The exact adapters include Endstone private Bedrock headers. Those headers require the same transitive SDK dependencies used by Endstone itself.

`conanfile.py` pins the relevant versions from Endstone 0.11.5/0.11.6. `scripts/build_exact.py` configures the public Endstone Cloudsmith remote, installs the graph with Conan 2, and passes the generated CMake toolchain into the exact build.

This replaces manual include-directory guessing. Missing headers such as `boost/functional/hash.hpp` and `entt/entt.hpp` are supplied by their package targets.
