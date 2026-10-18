# ZX Spectrum Chess Source Hashes

## SSD Image Locations on compute01

The original ZX Spectrum chess SSD images are stored locally on compute01:

```
/mnt/scratch/downloads/
├── SpectrumChess.z80              (Artic Computing, 1982)
├── SpectrumChess2.z80             (Artic Computing, 1982)
├── 16K_Superchess_(1983)(CP)(16K).z80    (Chris Whittington, 1983)
├── Chess_-_The_Turk_v1.3_(1983)(Oxford_Computer_Publishing).z80 (James Hutchby, 1982)
└── 3D_Chess_(1983)(Bennett,_Bill).z80    (Bill Bennett, 1983)
```

## Source Hashes

| Backend | Source File | SHA-256 Hash |
|---------|-------------|--------------|
| Spectrum Chess I | SpectrumChess.z80 | TODO - verify |
| Spectrum Chess II | SpectrumChess2.z80 | TODO - verify |
| 16K Superchess | 16K_Superchess.z80 | TODO - verify |
| The Turk | Chess_-_The_Turk_v1.3.z80 | TODO - verify |
| 3D Chess | 3D_Chess.z80 | TODO - verify |

## Verification Procedure

Before each evaluation campaign, verify source integrity:

```bash
cd /mnt/scratch/downloads/
sha256sum SpectrumChess.z80 SpectrumChess2.z80 \
    16K_Superchess.z80 Chess_-_The_Turk_v1.3.z80 3D_Chess.z80
```

Record hashes in this file and update the table above.

## License Notes

- **Artic Computing Chess (Spectrum Chess I & II)**: © Artic Computing, 1982
- **16K Superchess**: © Chris Whittington, 1983
- **The Turk**: © Oxford Computer Publishing, 1983
- **3D Chess**: © Bill Bennett, 1983

## Implementation Notes

The Python reimplementations in `chess_commander/backends/` are **experimental approximations**
based on classical chess evaluation techniques and reverse-engineered behavior patterns.

Important clarifications:

1. **Not verified reproductions**: The backends use standard piece-square tables and
   minimax search, but have NOT been verified against the original Z80 decision logic
   through emulator comparison.

2. **3D Chess is NOT a 3D variant**: The ThreeDChessBackend is a standard chess engine
   with a rank-control bonus. It does NOT implement the actual 3D chess variant with
   three stacked boards and cross-board movement.

3. **Source hashes pending**: SHA-256 hashes for the original Z80 images need to be
   computed and recorded before each evaluation campaign.

These backends are intended for:
- Learning and experimentation
- Testing the Chess Commander framework
- Educational purposes

They should NOT be used as historical recreations or for claims of matching the
original programs' behavior without emulator-based verification.

## References

- [`COMPLETE_ZX_SPECTRUM_BACKENDS.md`](../COMPLETE_ZX_SPECTRUM_BACKENDS.md) - Full backend analysis
- [`ZX_SPECTRUM_BACKENDS_INTEGRATION.md`](../ZX_SPECTRUM_BACKENDS_INTEGRATION.md) - Integration guide
- [`SUPERCHESS_INTEGRATION.md`](../SUPERCHESS_INTEGRATION.md) - Superchess specifics
