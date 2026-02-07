#!/bin/bash
# Fix Cloudflare authentication

echo "🔧 Fixing Cloudflare authentication..."
echo ""
echo "You need to run: cloudflared tunnel login"
echo ""
echo "IMPORTANT: After the browser opens and you click 'Authorize':"
echo "  1. The page will say 'Success! You've logged in.'"
echo "  2. It will download a file called 'cert.pem'"
echo "  3. You MUST move that file to: ~/.cloudflared/cert.pem"
echo ""
echo "The file usually downloads to your Downloads folder."
echo ""
read -p "Press Enter when you're ready to start..."

echo ""
echo "Running: cloudflared tunnel login"
cloudflared tunnel login

echo ""
echo "========================================"
echo "Did the browser open and download cert.pem?"
echo ""

# Check common download locations
CERT_LOCATIONS=(
    "$HOME/Downloads/cert.pem"
    "$HOME/Downloads/cert-*.pem"
    "$HOME/cert.pem"
    "$HOME/.cloudflared/cert.pem"
)

FOUND=""
for loc in "${CERT_LOCATIONS[@]}"; do
    if [ -f "$loc" ]; then
        FOUND="$loc"
        break
    fi
done

if [ -n "$FOUND" ]; then
    echo "✅ Found certificate at: $FOUND"
    echo ""
    read -p "Move it to ~/.cloudflared/? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mv "$FOUND" ~/.cloudflared/cert.pem
        chmod 600 ~/.cloudflared/cert.pem
        echo "✅ Certificate installed!"
    fi
else
    echo "❌ Could not find cert.pem automatically."
    echo ""
    echo "Please manually move the downloaded cert.pem to:"
    echo "  ~/.cloudflared/cert.pem"
    echo ""
    echo "Then run: chmod 600 ~/.cloudflared/cert.pem"
fi
