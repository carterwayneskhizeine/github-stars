# WebMCP Starter — Midnight Eats 🌙🍜

A single-file food delivery demo showcasing [WebMCP](https://github.com/webmachinelearning/webmcp), the proposed web standard that exposes structured tools for AI browser agents.

**Repo:** [https://github.com/Doriandarko/webmcp-starter](https://github.com/Doriandarko/webmcp-starter)

## What it demonstrates

**9 WebMCP tools** covering a full DoorDash-style ordering flow:

| Tool | API | What it does |
|------|-----|-------------|
| `search_restaurants` | Imperative | Filter by cuisine, name, dietary tag |
| `get_menu` | Imperative | Browse a restaurant's full menu |
| `add_to_cart` | Imperative | Add items with quantity + special instructions |
| `remove_from_cart` | Imperative | Remove items from cart |
| `get_cart` | Imperative | Read-only cart state + totals |
| `clear_cart` | Imperative | Empty the cart |
| `apply_promo_code` | Imperative | Apply WELCOME20, FREEDELIVERY, or SAVE5 |
| `get_order_status` | Imperative | Track a placed order |
| `checkout` | Declarative | HTML form with address, tip, payment |

## Setup

1. Install [C146+](https://www.google.com/chrome/canary/) (Canary)
2. Enable `chrome://flags/#enable-webmcp-testing`
3. Install the [Model Context Tool Inspector](https://chromewebstore.google.com/detail/model-context-tool-inspec/gbpdfapgefenggkahomfgkhfehlcenpd) extension
4. Open `food-app.html` locally in Chrome Canary
5. Click the extension → see all 9 tools → test with Gemini

## Test prompt

Paste this into the extension's agent prompt:

> I'm craving Italian food. Find me an Italian restaurant, add a margherita pizza, a carbonara, and a tiramisu. Apply WELCOME20. Checkout to 742 Evergreen Terrace, Apt 3B with a $5 tip on Visa.

## Resources

- [WebMCP Early Preview (Chrome)](https://developer.chrome.com/docs/ai/webmcp)
- [WebMCP Spec (GitHub)](https://github.com/webmachinelearning/webmcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
