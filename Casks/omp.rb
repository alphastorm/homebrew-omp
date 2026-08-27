cask "omp" do
  version "18.0.4-8bc938d5"
  sha256 "c3cf151472a56c8d3d3a9e8c66fc33bb7ba2bd1fb7e43f5b67c64f530ec56fed"

  github_token = ENV.fetch("HOMEBREW_GITHUB_API_TOKEN", nil)
  url "https://api.github.com/repos/alphastorm/homebrew-omp/releases/assets/527755112#omp-#{version}-darwin-arm64.tar.gz",
      verified: "api.github.com/repos/alphastorm/homebrew-omp/",
      header:   [
        "Accept: application/octet-stream",
        github_token && "Authorization: Bearer #{github_token}",
      ].compact
  name "Oh My Pi"
  desc "Downstream Oh My Pi coding harness with native Code Mode"
  homepage "https://github.com/alphastorm/omp-monorepo"

  depends_on macos: :tahoe
  depends_on arch: :arm64

  conflicts_with cask: "omp-beta"

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
