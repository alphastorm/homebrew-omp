cask "omp" do
  version "18.0.9-cross-platform-beta-2"
  sha256 "ba85e7aba6a6dba7d734e58d741c09798e8b3323f8abda0485bedafebc6c00c7"
  release_id = "18.0.9-hosted-macos-arm64-f4dcba581e4a"

  github_token = ENV.fetch("HOMEBREW_GITHUB_API_TOKEN", nil)
  url "https://api.github.com/repos/alphastorm/homebrew-omp/releases/assets/534356913#omp-18.0.9-macos-arm64.tar.gz",
      verified: "api.github.com/repos/alphastorm/homebrew-omp/",
      header:   [
        "Accept: application/octet-stream",
        github_token && "Authorization: Bearer #{github_token}",
      ].compact
  name "Oh My Pi"
  desc "Downstream Oh My Pi coding harness with native Code Mode"
  homepage "https://github.com/alphastorm/omp-monorepo"
  conflicts_with cask: "omp-beta"

  depends_on macos: :tahoe
  depends_on arch: :arm64

  stage_only true

  postflight do
    system_command "/usr/bin/xattr",
                   args:         ["-dr", "com.apple.quarantine", staged_path.to_s],
                   print_stderr: true
    system_command "#{staged_path}/install.sh",
                   args:         [staged_path.to_s],
                   print_stderr: true
  end

  uninstall_postflight do
    script = <<~SH
      release_id=$1
      data_root=${XDG_DATA_HOME:-$HOME/.local/share}/omp
      bin_root=${XDG_BIN_HOME:-$HOME/.local/bin}
      current_file=$data_root/current
      previous_file=$data_root/previous
      current=$(test -f "$current_file" && cat "$current_file" || true)
      previous=$(test -f "$previous_file" && cat "$previous_file" || true)

      if test "$current" = "$release_id"; then
        if test -n "$previous" && test -d "$data_root/releases/$previous"; then
          printf %s "$previous" >"$current_file"
          rm -f "$previous_file"
        else
          rm -f "$current_file" "$previous_file" "$bin_root/omp"
        fi
      elif test "$previous" = "$release_id"; then
        rm -f "$previous_file"
      fi
      rm -rf "$data_root/releases/$release_id"
    SH
    system_command "/bin/sh",
                   args:         ["-eu", "-c", script, "omp-beta-uninstall", release_id],
                   print_stderr: true
  end

  caveats <<~EOS
    This release installs into ~/.local/share/omp and links ~/.local/bin/omp.
    The current/previous files retain one rollback target across upgrades. Ensure
    ~/.local/bin is on your PATH.

    The binary is ad-hoc signed but not Developer ID-signed or notarized. The
    postflight removes com.apple.quarantine from the checksum-verified staged
    payload before installation; no deprecated Homebrew quarantine bypass is
    used. Integrity comes from this Cask's pinned archive SHA-256 plus the
    binary SHA-256 enforced by the shipped install.sh.
  EOS
end
