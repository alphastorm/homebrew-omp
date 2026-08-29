# homebrew-omp

Public Homebrew tap distributing pinned macOS arm64 builds of Oh My Pi. Stable OMP and invited
OMP NInfer early access use separate casks so a beta cannot silently replace the stable channel.

## Install

```sh
brew tap alphastorm/omp
brew install --cask alphastorm/omp/omp
```

The stable cask remains `omp`. Its currently pinned release is independent of the OMP NInfer beta.

## OMP NInfer beta

`omp-beta` is reserved for the invited
[`OMP NInfer`](https://github.com/alphastorm/omp-ninfer) early-access channel. Once the exact OMP
archive exists, maintainers create `omp-beta.rb` on the beta release branch and bind that
40-character branch commit in the product `candidate` manifest. A bounded candidate-publication
window fast-forwards the same commit to the tap's `main`; clean-machine acceptance then exercises
the ordinary public tap. The product tag remains withheld until the manifest is `ready`. While the
manifest is `draft`, there is no supported beta install command.

The current published prerelease is `v0.2.0-beta.1`; follow its
[exact early-access setup](https://github.com/alphastorm/omp-ninfer/blob/v0.2.0-beta.1/docs/QUICKSTART.md).
That procedure resolves `homebrew_cask_revision` from the product manifest, compares the current
`omp-beta.rb` bytes with that commit, disables auto-update for the install transaction, and only
then installs. A bare `brew install --cask omp-beta` is not the release-integrity procedure.

The two casks conflict because both own the same immutable release root and
`~/.local/bin/omp` launcher. They are channels, not side-by-side commands. To return to stable:

```sh
brew uninstall --cask alphastorm/omp/omp-beta
brew install --cask alphastorm/omp/omp
```

The beta cask installs OMP only. NInfer, the Qwen artifact, SSH tunnel, and fail-closed provider
configuration follow the exact OMP NInfer product manifest and quickstart; this tap must not
duplicate or weaken those pins.

## Maintainer beta cut

The OMP distribution lane remains the single source of archive, version, URL, and installer logic.
After it packs and uploads the exact OMP asset, commit an ordinary source cask that names the
archive's actual installer contract, then mechanically rebrand only the channel-owned fields. The
current hosted-client archive ships `install.sh`; the verifier downloads the release asset and
checks that entrypoint, its release identity, and its binary hash before accepting the cask:

```sh
cd "$HOMEBREW_OMP_REPO"
python3 scripts/render_beta_cask.py \
  --input release-sources/omp-18.0.9-cross-platform-beta-2.rb \
  --output Casks/omp-beta.rb
python3 scripts/render_beta_cask.py \
  --input release-sources/omp-18.0.9-cross-platform-beta-2.rb \
  --output Casks/omp-beta.rb --check
python3 -m unittest discover -s tests -v
GITHUB_TOKEN="$(gh auth token)" python3 scripts/verify_cask.py \
  --cask Casks/omp-beta.rb --token omp-beta --allow-draft
```

Commit that cask on the exact beta release branch. Its 40-character commit is the
`homebrew_cask_revision` in the OMP NInfer product manifest. After the product manifest reaches its
fully pinned `candidate` state, a bounded candidate-publication window fast-forwards that same
commit to the tap's `main`. Clean-machine acceptance then uses the ordinary public tap while
verifying that its HEAD is the recorded revision. The product tag remains withheld until acceptance
passes; never regenerate or amend the accepted cask.

## What it installs

Nothing under the Homebrew prefix. The cask is `stage_only`, and a `postflight`
runs the shipped `install.sh`, which owns the current hosted-client layout:

```
~/.local/share/omp/
  releases/<release-id>/omp      immutable client binary
  current                        active release id
  previous                       rollback release id
~/.local/bin/omp                 release-resolving launcher
```

`~/.local/bin` must be on `PATH`. Homebrew never links a binary here, because
`current` is authoritative and a second pointer could disagree with it.

## Integrity

Three independent checks, none of which subsumes the others:

- Homebrew verifies the downloaded archive against the `sha256` this cask pins.
- `install.sh` re-verifies the client binary against the SHA-256 in
  `client-release.json` before copying it into the immutable release directory.
- The launcher resolves `current` from `HOME` on every invocation, so a copy
  running under a different `HOME` uses that isolated tree.

Archives are packed reproducibly, so the published digest can be re-derived from
the immutable release tree without trusting the upload.

## Versions and channels

`version` is the digest-qualified build id, for example `18.0.1-eede9df3`, not
the upstream version alone. Two downstream builds of one upstream tag are
different artifacts: they get different Caskroom slots and different immutable
asset URLs, so `brew upgrade` moves between them correctly and two builds never
collide on one digest. Replacing the asset behind an already-published build id
is permissible only while nothing has installed it; `18.0.3-4892e25b` was
replaced once under that rule, to ship the `install-release` guard that keeps a
release the installed `current` or `previous` pointers still name.

Stable and beta version identities use the same digest-qualified rule. `omp-beta` may point only to
the OMP build named by the current OMP NInfer prerelease; moving a mutable beta label to different
bytes without a new product version is prohibited.

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
