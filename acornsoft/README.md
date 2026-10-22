# Acornsoft backend

This backend targets Acornsoft Chess V2.1 for the BBC Micro.

Reference image:

- `/mnt/scratch/downloads/Acornsoft_Chess_V2.1.ssd`
- SHA-256: `72d14af1fced97aca88e6532fac54b213b7b81b819a5a8a435be39837afb037b`

The native adapter is implemented at
`chess_commander.backends.acornsoft.AcornsoftChessBackend`. It isolates the
strategy behind the common match interface and does not make the shared
referee or persistence layer depend on Acornsoft-specific board or move
representations.

The emulator remains the behavioural oracle. Live T14 observations are
recorded outside Git while exact move-fidelity qualification continues.
