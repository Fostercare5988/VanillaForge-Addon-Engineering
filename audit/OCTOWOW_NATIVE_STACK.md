# OctoWoW Deployed Native Stack Audit

> **Hardware / Engine Abstraction Layer for the Authoritative OctoWoW Client**
> Current file identity refreshed 19 October 2026; historical runtime details remain dated evidence.

---

## 1. Native Extension Inventory

| Extension Module | File Size | SHA256 Checksum | Deployed Version | Loader Status | Provenance & Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ClassicAPI.dll`** | 1,512,448 | `ae88fc0461b58eff37171e10015ddaf8c27b1f428794c4ff927429389fc2535b` | **v1.16.0 release asset** | Listed via `dlls.txt`; runtime not yet checked | `[DEPLOYED FACT]` Exact SHA-256/size match to upstream release asset (`tag v1.16.0`, commit `99de6375...`). Installed 19 October; full restart required. Earlier 767-registration log is from v1.15.16 and is historical. |
| **`SuperWoWhook.dll`** | 1,000,448 | `bd214b32c878649e94ce654835946bd05e0ce7710e8f01bae10d8ab50a89351d` | **v2.2** | Loaded via `dlls.txt` | `[DEPLOYED FACT]` Binary embeds string `SUPERWOW_VERSION="2.2"` and `SUPERWOW_STRING="SuperWoW 2.2 by Balake"`. |
| **`nampower.dll`** | 829,952 | `96af1722ee6b1a76cbb11e59e452fe54a83f54a3da80ae24f9c7571a0a6392fe` | **v4.6.2** | Loaded via `dlls.txt` | `[DEPLOYED FACT]` Startup log `nampower_debug.log` line 1: `Loading nampower v4.6.2`. Registers `GetNampowerVersion` and extensive cast/combat CVars. |
| **`UnitXP_SP3.dll`** | 202,240 | `74a0a80aef02be28187fd67e9ec3945d54828ef3302a827754b4c40b69cdaed8` | **SP3 Build 90** | Loaded via `dlls.txt` | `[DEPLOYED FACT]` PE TimeDateStamp: `1774797347` (2026-03-29 15:15:47 UTC). Registers `UnitXP(...)` command dispatcher. |
| **`AuctionQueryThrottle.dll`** | 92,672 | `720b7ad72941206249df23cb9d36addafa2634f190081f7b33834b84af184f5e` | N/A | Loaded via `dlls.txt` | `[DEPLOYED FACT]` Paces `QueryAuctionItems` calls to eliminate server packet flood disconnects during auction scans. |
| **`transmogfix.dll`** | 12,800 | `cd9e4c6ce033b0923cf045269f590f5e0b886bd03f43bd81406670d781452210` | WeirdUtils | Loaded via `dlls.txt` | `[DEPLOYED FACT]` Hook for custom transmogrification item display; exports `GetWeirdUtilsVersion`. |
| **`dxgi.dll`** | 5,877,774 | `abd1449dc28d536a4289c256ae7f4b6bbd15fa552792b7170c2ddece473c8bda` | DXVK 10.0.17763.1 | Implicit runtime hook | `[DEPLOYED FACT]` DirectX-to-Vulkan graphics translation pipeline. Never an addon Lua dependency. |
| **`VanillaFixes.exe`** | 88,576 | `228d7bb5e3b5b0c2062d6c5f40c38c2a173e4c80d8a5d9e4077be800431b48a3` | Native Loader | Process launcher | `[DEPLOYED FACT]` Custom 1.12.1 memory patcher & DLL injector. |
| **`VanillaHelpers.dll`** | 254,976 | `1e74ddf6484c23482550d5f9e5f9d291085c4ac538d3b3ed9d87155521841196` | Loader helper | Injected by loader | `[DEPLOYED FACT]` Win32 windowing & crash handler utilities. |
| **`VanillaMultiMonitorFix.dll`** | 28,160 | `7fa033e744c4b8794a4c97a45d563a8870264244bfa1e478a1c0f85e0c6e3371` | Multi-monitor hook | Injected by loader | `[DEPLOYED FACT]` Multi-monitor resolution clamping fix. |
| **`VfPatcher.dll`** | 72,704 | `f283b6b5ad8042e7995eff9768c150042dd47de6e5f00ffe530d2e67743df81d` | Runtime patcher | Injected by loader | `[DEPLOYED FACT]` Binary hook patcher for client engine addresses. |

---

## 2. Loader Configuration (`dlls.txt`)

The loader parses `C:\Users\Fostercare\Desktop\client-2026-10-10\dlls.txt`:

```text
SuperWoWhook.dll
ClassicAPI.dll
nampower.dll
UnitXP_SP3.dll
OctoLogin.dll
transmogfix.dll
AuctionQueryThrottle.dll
d3d9.dll
```

### Analysis of Loader Order:
1. `SuperWoWhook.dll` is initialized first, hooking raw client engine functions (targeting, combat log, GUID routing).
2. `ClassicAPI.dll` initializes second, binding modern namespaces and hooking FrameScript registration tables.
3. `nampower.dll` initializes third, configuring high-frequency spell cast queueing and nameplate filters.
4. `UnitXP_SP3.dll` initializes fourth, attaching camera height, FOV, and custom nameplate positioning.
5. `OctoLogin.dll`, `transmogfix.dll` and `AuctionQueryThrottle.dll` appear later in the configured order; their runtime behavior is outside this ClassicAPI refresh.
6. `d3d9.dll` is listed and present in the current client root. File identity does not by itself prove the active rendering path or runtime loading.

---

## 3. Client Capability vs Addon Dependency Rule

An architectural tenet of VanillaForge:
> **A globally deployed DLL is a CLIENT CAPABILITY. Addon requirements still follow the declared support policy.**

- All 16 maintained VanillaForge addons now require ClassicAPI v1.16.0+ by explicit maintainer policy, even where a specific addon does not call a newly added API. TOC minimum metadata, `!!!ClassicAPI` dependency and startup guard must agree.
- Other components remain capability-driven: declare a dependency only when the addon requires that component to load (for example, optional `UnitGUID` use does not require SuperWoW).
- Never declare `DXVK`, `VanillaFixes`, or `AuctionQueryThrottle` as addon dependencies.
- Where an API like `UnitGUID` (SuperWoW) or `UnitXP` is consumed for optional quality-of-life enhancements, addons must use safe feature detection (`if UnitGUID then ... end`) rather than adding a hard dependency.
