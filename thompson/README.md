# Thompson backend

This backend targets D. Thompson's Computer Concepts Chess 2.32/1 for the
32K BBC Micro.

Reference image:

- `/mnt/scratch/downloads/Computer_Concepts_Chess_DThompson.ssd`
- SHA-256: `80120f0f346194a388ebb7152d9970ec635612fee38b733d7002f113b941eb95`

The backend adapter will isolate the original chess logic behind the common
match interface. It must not make the shared referee or persistence layer
depend on Thompson-specific board or move representations.
