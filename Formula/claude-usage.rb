class ClaudeUsage < Formula
  include Language::Python::Virtualenv

  desc "SwiftBar plugin that monitors Claude.ai usage in the macOS menu bar"
  homepage "https://github.com/sigreyo/homebrew-claude-usage"
  url "https://github.com/sigreyo/homebrew-claude-usage/archive/refs/tags/v0.1.3.tar.gz"
  sha256 "c09fb81f307fcf7036268a894c1a3963de37cbdf074c416e26c60c8537ccbf3a"
  license "MIT"

  depends_on "python@3.13"
  depends_on :macos

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/e0/2d/a891ca51311197f6ad14a7ef42e2399f36cf2f9bd44752b3dc4eab60fdc5/certifi-2026.1.4.tar.gz"
    sha256 "ac726dd470482006e014ad384921ed6438c457018f4b3d204aea4281258b2120"
  end

  resource "charset-normalizer" do
    url "https://files.pythonhosted.org/packages/13/69/33ddede1939fdd074bce5434295f38fae7136463422fe4fd3e0e89b98062/charset_normalizer-3.4.4.tar.gz"
    sha256 "94537985111c35f28720e43603b8e7b43a6ecfb2ce1d3058bbe955b73404e21a"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/6f/6d/0703ccc57f3a7233505399edb88de3cbd678da106337b9fcde432b65ed60/idna-3.11.tar.gz"
    sha256 "795dafcc9c04ed0c1fb032c2aa73654d8e8c5023a7df64a53f39190ada629902"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/c9/74/b3ff8e6c8446842c3f5c837e9c3dfcfe2018ea6ecef224c710c85ef728f4/requests-2.32.5.tar.gz"
    sha256 "dbba0bac56e100853db0ea71b82b4dfd5fe2bf6d3754a8893c3af500cec7d7cf"
  end

  resource "urllib3" do
    url "https://files.pythonhosted.org/packages/c7/24/5f1b3bdffd70275f6661c76461e25f024d5a38a46f04aaca912426a2b1d3/urllib3-2.6.3.tar.gz"
    sha256 "1b62b6884944a57dbe321509ab94fd4d3b307075e0c2eae991ac71ee15ad38ed"
  end

  resource "browser-cookie3" do
    url "https://files.pythonhosted.org/packages/e0/e1/652adea0ce25948e613ef78294c8ceaf4b32844aae00680d3a1712dde444/browser_cookie3-0.20.1.tar.gz"
    sha256 "6d8d0744bf42a5327c951bdbcf77741db3455b8b4e840e18bab266d598368a12"
  end

  resource "lz4" do
    url "https://files.pythonhosted.org/packages/57/51/f1b86d93029f418033dddf9b9f79c8d2641e7454080478ee2aab5123173e/lz4-4.4.5.tar.gz"
    sha256 "5f0b9e53c1e82e88c10d7c180069363980136b9d7a8306c4dca4f760d60c39f0"
  end

  resource "pycryptodomex" do
    url "https://files.pythonhosted.org/packages/c9/85/e24bf90972a30b0fcd16c73009add1d7d7cd9140c2498a68252028899e41/pycryptodomex-3.23.0.tar.gz"
    sha256 "71909758f010c82bc99b0abf4ea12012c98962fbf0583c2164f8b84533c2e4da"
  end

  def install
    # Create virtualenv and install dependencies
    venv = virtualenv_create(libexec, "python3.13")
    venv.pip_install resources

    # Copy plugin scripts into libexec (co-located with the venv)
    libexec.install "src/claude-usage.5m.py"
    libexec.install "src/scrape_usage.py"

    # Rewrite shebangs to use the virtualenv python (so imports resolve correctly)
    venv_python = libexec/"bin"/"python3"
    [libexec/"claude-usage.5m.py", libexec/"scrape_usage.py"].each do |script|
      inreplace script, "#!/usr/bin/env python3", "#!#{venv_python}"
    end

    # Generate wrapper scripts in bin/
    (bin/"claude-usage-setup").write <<~BASH
      #!/bin/bash
      set -euo pipefail

      PLUGIN_DIR="${HOME}/Library/Application Support/SwiftBar"
      LIBEXEC="#{libexec}"

      echo "Claude Usage - SwiftBar Plugin Setup"
      echo "====================================="
      echo ""

      # Detect SwiftBar plugin directory
      # Check if SwiftBar is installed and get its plugin directory
      SWIFTBAR_PLIST="${HOME}/Library/Preferences/com.ameba.SwiftBar.plist"
      if [ -f "$SWIFTBAR_PLIST" ]; then
        CUSTOM_DIR=$(defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null || true)
        if [ -n "$CUSTOM_DIR" ]; then
          PLUGIN_DIR="$CUSTOM_DIR"
        fi
      fi

      echo "SwiftBar plugin directory: $PLUGIN_DIR"
      mkdir -p "$PLUGIN_DIR"

      # Create symlink for the plugin
      LINK="$PLUGIN_DIR/claude-usage.5m.py"
      if [ -L "$LINK" ]; then
        echo "Updating existing symlink..."
        rm "$LINK"
      elif [ -f "$LINK" ]; then
        echo "Backing up existing plugin to ${LINK}.bak"
        mv "$LINK" "${LINK}.bak"
      fi
      ln -s "$LIBEXEC/claude-usage.5m.py" "$LINK"
      chmod +x "$LIBEXEC/claude-usage.5m.py"
      echo "Symlinked plugin into SwiftBar directory."

      # Create config directory
      mkdir -p "${HOME}/.config/claude-usage"

      echo ""
      echo "Setup complete!"
      echo ""
      echo "Next steps:"
      echo "  1. Open SwiftBar (brew install --cask swiftbar)"
      echo "  2. Make sure you're logged into claude.ai in your browser (Chrome, Brave, Firefox, or Safari)"
      echo "  3. The usage monitor will appear in your menu bar"
    BASH

    (bin/"claude-usage-scrape").write <<~BASH
      #!/bin/bash
      exec "#{libexec}/bin/python3" "#{libexec}/scrape_usage.py" "$@"
    BASH

    # Make wrapper scripts executable
    chmod 0755, bin/"claude-usage-setup"
    chmod 0755, bin/"claude-usage-scrape"
  end

  def caveats
    <<~EOS
      To set up the Claude usage monitor:

        1. Install SwiftBar (if not already installed):
             brew install --cask swiftbar

        2. Open SwiftBar — when prompted for a Plugin Folder, pick any folder
           (e.g. ~/Library/Application Support/SwiftBar).

        3. Run the setup script:
             claude-usage-setup

        4. Make sure you're logged into claude.ai in your browser
           (Chrome, Brave, Firefox, or Safari).
           The usage monitor will appear in your menu bar.

      Data is stored in ~/.config/claude-usage/
    EOS
  end

  test do
    assert_match "usage", shell_output("#{bin}/claude-usage-scrape 2>&1", 1)
  end
end
