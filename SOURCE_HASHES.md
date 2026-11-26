# ZX Spectrum Chess Source Hashes

## Source Image Locations on compute01

**Present (verified, 2026-11-26):**

```
/mnt/marmot/project-data/chess-commander/
├── Acornsoft_Chess_V2.1.ssd              (BBC Micro, 6502)
└── Computer_Concepts_Chess_DThompson.ssd  (BBC Micro, 6502)
```

**Not present (must be re-pulled before Phase 3 fidelity gates):**

The 5 ZX Spectrum z80 sources were working files in volatile `/tmp`
(cleared on reboot). Re-pull from World of Spectrum / archive.org before
re-running `z80disasm.py` for the fidelity comparison:

```
SpectrumChess.z80              (Artic Computing, 1982)
SpectrumChess2.z80             (Artic Computing, 1982)
16K_Superchess_(1983)(CP)(16K).z80    (Chris Whittington, 1983)
Chess_-_The_Turk_v1.3_(1983)(Oxford_Computer_Publishing).z80 (James Hutchby, 1982)
3D_Chess_(1983)(Bennett,_Bill).z80    (Bill Bennett, 1983)
```

## Source Hashes

| Backend | Source File | SHA-256 Hash |
|---------|-------------|--------------|
| Acornsoft Chess V2.1 | Acornsoft_Chess_V2.1.ssd | `72d14af1fced97aca88e6532fac54b213b7b81b819a5a8a435be39837afb037b` |
| Thompson Chess | Computer_Concepts_Chess_DThompson.ssd | `80120f0f346194a388ebb7152d9970ec635612fee38b733d7002f113b941eb95` |
| Spectrum Chess I | SpectrumChess.z80 | TODO — re-pull and verify |
| Spectrum Chess II | SpectrumChess2.z80 | TODO — re-pull and verify |
| 16K Superchess | 16K_Superchess_(1983)(CP)(16K).z80 | TODO — re-pull and verify |
| The Turk | Chess_-_The_Turk_v1.3.z80 | TODO — re-pull and verify |
| 3D Chess | 3D_Chess_(1983)(Bennett,_Bill).z80 | TODO — re-pull and verify |

## Verification Procedure

Before each evaluation campaign, verify source integrity:

```bash
cd /mnt/marmot/project-data/chess-commander/
sha256sum Acornsoft_Chess_V2.1.ssd Computer_Concepts_Chess_DThompson.ssd
```

For the Spectrum z80 sources, re-pull first, then:

```bash
sha256sum SpectrumChess.z80 SpectrumChess2.z80 \
    16K_Superchess_(1983)(CP)(16K).z80 \
    Chess_-_The_Turk_v1.3_(1983)(Oxford_Computer_Publishing).z80 \
    3D_Chess_(1983)(Bennett,_Bill).z80
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
