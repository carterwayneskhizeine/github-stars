# Claude Code Buddy Collection

A visual gallery of all 18 companion species discovered in the **Claude Code** buddy system, reconstructed from leaked source code analysis.

![Preview](preview.png)

**Live Page:** [claude-code-buddy-collection.html](claude-code-buddy-collection.html) — open directly in any browser.

## Background

In March 2026, a snapshot of the Claude Code source code was leaked, revealing a hidden companion (buddy) system embedded inside the CLI. This was not a casual Easter egg — it was a fully productized desktop pet feature with:

- **Deterministic generation** — each user gets a unique companion derived from their user ID via seeded PRNG (mulberry32)
- **Bones + Soul architecture** — physical traits (species, rarity, eyes, hat, stats) are regenerated deterministically, while personality traits (name, personality) are persisted
- **ASCII sprite engine** — multi-frame animated sprites with hat overlays, eye substitution, and a narrow-terminal face mode
- **Rarity system** — 5 tiers with weighted rolling (Common 60%, Uncommon 25%, Rare 10%, Epic 4%, Legendary 1%)
- **1% shiny chance** — a rare sparkle variant, inspired by collectible game mechanics
- **Personality stats** — DEBUGGING, PATIENCE, CHAOS, WISDOM, SNARK — each companion has a peak stat and a dump stat
- **Anti-cheat design** — bones are never persisted to config, so editing config files cannot fake a rarity

The feature was gated behind a `BUDDY` feature flag and tied to an April 1–7, 2026 teaser window with rainbow-highlighted `/buddy` command input.

## What's in This Repo

| File | Description |
|------|-------------|
| `claude-code-buddy-collection.html` | A single-file HTML page that displays all 18 species as interactive cards with ASCII sprites, eye variants, hat options, stats, rarity indicators, and shiny effects |
| `README.md` | This file |

## The 18 Species

| Species | Rarity | Default Hat | Emoji |
|---------|--------|-------------|-------|
| Duck | Common | — | 🦆 |
| Goose | Common | — | 🪿 |
| Blob | Common | — | 🫧 |
| Cat | Rare | Wizard Hat | 🐱 |
| Dragon | Legendary | Crown | 🐉 |
| Octopus | Uncommon | — | 🐙 |
| Owl | Rare | Top Hat | 🦉 |
| Penguin | Uncommon | Beanie | 🐧 |
| Turtle | Common | — | 🐢 |
| Snail | Common | — | 🐌 |
| Ghost | Epic | Halo | 👻 |
| Axolotl | Epic | Propeller | 🦎 |
| Capybara | Rare | Tiny Duck | 🐹 |
| Cactus | Uncommon | — | 🌵 |
| Robot | Rare | — | 🤖 |
| Rabbit | Uncommon | — | 🐰 |
| Mushroom | Common | — | 🍄 |
| Chonk | Common | — | 🐈 |

## System Design Highlights

### Rarity Weights
```
Common:    60%  ★
Uncommon:  25%  ★★
Rare:      10%  ★★★
Epic:       4%  ★★★★
Legendary:  1%  ★★★★★
```

### Eye Variants (6)
`·` `✦` `×` `◉` `@` `°`

### Hat Options (7)
Crown, Top Hat, Propeller, Halo, Wizard, Beanie, Tiny Duck

### Stats
Each companion rolls 5 personality stats with a rarity-based floor:
- **Common** floor: 5 | **Uncommon**: 15 | **Rare**: 25 | **Epic**: 35 | **Legendary**: 50
- One peak stat (high) and one dump stat (low) per companion

### Shiny
1% chance. Shiny companions get a golden shimmer overlay and sparkle particle effects.

## Technical Details

The HTML page faithfully reproduces the sprite rendering logic from the original source:

- `{E}` placeholder substitution for eye variants (from `sprites.ts`)
- Hat overlay insertion at the top sprite line (from `sprites.ts`)
- Multi-frame idle animation with bobbing effect (from `CompanionSprite.tsx`)
- Narrow-terminal face rendering for compact display (from `sprites.ts`)
- Exact ASCII art preserved from the original `BODIES` constant

## Source Code References

The buddy system was spread across multiple files in the Claude Code codebase:

- `src/buddy/types.ts` — Type definitions (CompanionBones, CompanionSoul, Rarity, Species)
- `src/buddy/companion.ts` — Deterministic generation, rolling, and anti-cheat logic
- `src/buddy/sprites.ts` — ASCII sprite definitions and rendering engine
- `src/buddy/prompt.ts` — System prompt injection for companion identity
- `src/buddy/CompanionSprite.tsx` — React/Ink terminal UI component with animation
- `src/buddy/useBuddyNotification.tsx` — April Fools teaser notification system
- `src/commands.ts` — `/buddy` command registration behind feature gate
- `src/utils/config.ts` — Companion soul persistence in global config

## License

This is a fan-made documentation project for educational and archival purposes. All original concept and design belong to Anthropic.
