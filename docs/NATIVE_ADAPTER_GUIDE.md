# Native adapter guide

Create one adapter directory per exact BDS build. An adapter must verify every signature before advertising a capability.

Required operations:

- resolve dimension and chunk without forcing unsafe loads
- capture block runtime ID and states
- locate `BlockActor`
- serialize and deserialize the actor's `CompoundTag`
- bridge container slots
- mark the actor/chunk dirty
- trigger the correct client update

Do not ship offsets copied from another BDS version. On any verification failure, return `Unsupported` and leave the world untouched.
