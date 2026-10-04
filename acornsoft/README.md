# Acornsoft backend

This backend targets Acornsoft Chess V2.1 for the BBC Micro.

Reference image:

- `/mnt/scratch/project-data/chess-commander/Acornsoft_Chess_V2.1.ssd`
- SHA-256: `72d14af1fced97aca88e6532fac54b213b7b81b819a5a8a435be39837afb037b`

The backend adapter will isolate the original chess logic behind the common
match interface. It must not make the shared referee or persistence layer
depend on Acornsoft-specific board or move representations.
