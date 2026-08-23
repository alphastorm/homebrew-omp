# homebrew-omp

Private Homebrew tap distributing prebuilt macOS arm64 builds of the downstream
Oh My Pi fork.

## Install

```sh
brew tap alphastorm/omp
HOMEBREW_GITHUB_API_TOKEN=$(gh auth token) brew install --cask alphastorm/omp/omp
```

The token is needed only to download the release asset from this private
repository. Homebrew's cask downloader is the generic curl strategy and does not
consult the Git credential helper that authenticates the tap clone itself.

## What it installs

Nothing under the Homebrew prefix. The cask is `stage_only`, and a `postflight`
runs the shipped `install-release`, which owns the real layout:

```
~/.local/lib/omp-code-mode/
  releases/<version>-<sha256>/   immutable release tree
  current -> releases/<...>      active release
  previous -> releases/<...>     rollback target
  omp -> current/omp-code-mode
~/.local/bin/omp -> current/omp-code-mode-launcher
```

`~/.local/bin` must be on `PATH`. Homebrew never links a binary here, because
`current` is authoritative and a second pointer could disagree with it.

## Integrity

Three independent checks, none of which subsumes the others:

- Homebrew verifies the downloaded archive against the `sha256` this cask pins.
- `install-release` re-verifies every member's SHA-256 and permission mode from
  the release's own `release.json` after transport, and refuses any path the
  manifest does not declare. Aggregate archive integrity does not localise
  extraction or staging damage.
- The launcher re-verifies the whole release against `release.json` on every
  launch. It resolves the release root from `HOME`, so running a copy against a
  different `HOME` verifies and runs that tree, not the one beside the launcher.

Archives are packed reproducibly, so the published digest can be re-derived from
the immutable release tree without trusting the upload.

## Versions

`version` is the digest-qualified build id, for example `18.0.1-eede9df3`, not
the upstream version alone. Two downstream builds of one upstream tag are
different artifacts: they get different Caskroom slots and different immutable
asset URLs, so `brew upgrade` moves between them correctly and two builds never
collide on one digest. Replacing the asset behind an already-published build id
is permissible only while nothing has installed it; `18.0.3-4892e25b` was
replaced once under that rule, to ship the `install-release` guard that keeps a
release the installed `current` or `previous` pointers still name.

## Signing

Builds are ad-hoc signed. Apple silicon requires that: it refuses to execute
native arm64 code with no valid signature attached. They are not Developer
ID-signed or notarized, which needs an Apple Developer Program membership. An
ad-hoc signature does not make Gatekeeper treat the publisher as an identified
developer, so a quarantined download is still refused, and `install-release`
removes `com.apple.quarantine` from the tree it installs.

Nothing re-signs the binaries after the build. Signing rewrites the Mach-O and
would change digests that `release.json` pins and the launcher re-verifies on
every launch.

No `--no-quarantine` flag is involved; Homebrew removed it in
[Homebrew/brew#20755](https://github.com/Homebrew/brew/issues/20755).

## Uninstall

```sh
brew uninstall --cask alphastorm/omp/omp
```

`uninstall_postflight` runs before Homebrew purges the staged copy, so the
shipped uninstaller restores `current` from `previous` and removes only the
release it installed.
