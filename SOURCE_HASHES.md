# ZX Spectrum Chess Source Hashes

## Source Image Locations on compute01

**Present (verified, 2026-11-26):**

```
/mnt/marmot/project-data/chess-commander/
├── Acornsoft_Chess_V2.1.ssd              (BBC Micro, 6502)
├── Computer_Concepts_Chess_DThompson.ssd  (BBC Micro, 6502)
└── sources/                               (re-pulled 2026-11-26, World of Spectrum)
    ├── 16K_Superchess.tap
    ├── SpectrumChess_I.tzx
    ├── SpectrumChess_II.tzx
    ├── 3D_Chess.z80
    └── The_Turk.tzx
```

**Re-pulled 2026-11-26** from World of Spectrum and extracted to
`/mnt/marmot/project-data/chess-commander/sources/` (listed above). The
canonical archive.org / World of Spectrum distributions are tape/snapshot
images (`.tap` / `.tzx` / `.z80`), not the disassembled `.z80` binaries the
original table referenced — the `.z80` disassemblies must be regenerated from
these images before `z80disasm.py` can run for the fidelity comparison.

## Source Hashes

| Backend | Source File | SHA-256 Hash |
|---------|-------------|--------------|
| Acornsoft Chess V2.1 | Acornsoft_Chess_V2.1.ssd | `72d14af1fced97aca88e6532fac54b213b7b81b819a5a8a435be39837afb037b` |
| Thompson Chess | Computer_Concepts_Chess_DThompson.ssd | `80120f0f346194a388ebb7152d9970ec635612fee38b733d7002f113b941eb95` |
| Spectrum Chess I | sources/SpectrumChess_I.tzx | `ec5de4585b8c07f258b9fd6739eb02495c8c2b1b8814a7a38e1f5aab17d7c060` |
| Spectrum Chess II | sources/SpectrumChess_II.tzx | `99a8f5929b2e04c74449fdd5fe154814e40cf4570d1731774288183a05176d36` |
| 16K Superchess | sources/16K_Superchess.tap | `840c3f9631df50f048fa0e3b1e79f81bfe7ac666277b32e90edbb8e47f30887b` |
| The Turk | sources/The_Turk.tzx | `5b918a18db6e3d5aeffbb999d74af7a542c08021977b3458479795793fa13bb9` |
| 3D Chess | sources/3D_Chess.z80 | `f1cdc79bec9678005ac206a1d8c00e8e7826ea7e24a11a0d22e63df926e386a0` |

> The five Spectrum hashes above are for the **re-pulled archive images**
> (tape/snapshot), not the disassembled `.z80` binaries. The disassembly
> hashes are recorded after `z80disasm.py` regenerates them from these images.

## Verification Procedure

Before each evaluation campaign, verify source integrity:

```bash
cd /mnt/marmot/project-data/chess-commander/
sha256sum Acornsoft_Chess_V2.1.ssd Computer_Concepts_Chess_DThompson.ssd
```

For the Spectrum sources (already re-pulled to `sources/`), verify directly:

```bash
cd /mnt/marmot/project-data/chess-commander/
sha256sum sources/SpectrumChess_I.tzx sources/SpectrumChess_II.tzx \
    sources/16K_Superchess.tap \
    sources/The_Turk.tzx \
    sources/3D_Chess.z80
```

Record hashes in this file and update the table above.

## License Notes

- **Artic Computing Chess (Spectrum Chess I & II)**: © Artic Computing, 1982
- **16K Superchess**: © Chris Whittington, 1983
- **The Turk**: © Oxford Computer Publishing, 1983
- **3D Chess**: © Bill Bennett, 1983

These are historical programs. The Python reimplementations in `chess_commander/backends/`
are based on reverse-engineered behavior from disassembly and are not direct copies of
the original code.

## References

- [`COMPLETE_ZX_SPECTRUM_BACKENDS.md`](../COMPLETE_ZX_SPECTRUM_BACKENDS.md) - Full backend analysis
- [`ZX_SPECTRUM_BACKENDS_INTEGRATION.md`](../ZX_SPECTRUM_BACKENDS_INTEGRATION.md) - Integration guide
- [`SUPERCHESS_INTEGRATION.md`](../SUPERCHESS_INTEGRATION.md) - Superchess specifics
