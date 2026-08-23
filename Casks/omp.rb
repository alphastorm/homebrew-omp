cask "omp" do
  version "18.0.1-eede9df3"
  sha256 "10bdd13a5ca7d6726b10ed563e916e8c926728eb6e3b83f1e6223770cc035ede"

  github_token = ENV.fetch("HOMEBREW_GITHUB_API_TOKEN", nil)
  url "https://github.com/alphastorm/homebrew-omp/releases/download/omp-#{version}/omp-#{version}-darwin-arm64.tar.gz",
      verified: "github.com/alphastorm/",
      header:   github_token && "Authorization: Bearer #{github_token}"
  name "Oh My Pi"
  desc "Downstream Oh My Pi coding harness with native Code Mode"
  homepage "https://github.com/alphastorm/omp-monorepo"

  depends_on macos: :tahoe
  depends_on arch: :arm64

  stage_only true

  postflight do
    system_command "#{staged_path}/install-release",
                   args:         ["--activate"],
                   print_stderr: true
  end

  uninstall_postflight do
    system_command "#{staged_path}/install-release",
                   args:         ["--uninstall"],
                   print_stderr: true
  end

  caveats <<~EOS
    This release installs into ~/.local/lib/omp-code-mode and links
    ~/.local/bin/omp, so the existing current/previous pointers keep deciding
    which release is live. Ensure ~/.local/bin is on your PATH.

    The binaries are ad-hoc signed but not Developer ID-signed or notarized, so
    Gatekeeper still refuses a quarantined copy. The shipped installer removes
    com.apple.quarantine from the tree it installs; no --no-quarantine flag is
    used, and Homebrew no longer has one. Integrity comes from this Cask's
    pinned sha256 plus the per-file digests the installer re-verifies from
    release.json.
  EOS
end
