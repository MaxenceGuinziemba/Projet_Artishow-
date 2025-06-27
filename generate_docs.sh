#!/bin/bash
# Quick script to generate Python documentation with Sphinx

# Make sure we're in the project root
cd "$(dirname "$0")"

# Set PYTHONPATH to include current directory
export PYTHONPATH=$PWD:$PYTHONPATH

# Run the documentation generator
python src/utils/generate_docs.py

# Check if documentation was generated successfully
if [ $? -eq 0 ]; then
    echo "Documentation generated successfully!"
    
    # Open the documentation in the default browser (if available)
    if command -v open >/dev/null 2>&1; then
        echo "Opening documentation in browser..."
        open docs/build/html/index.html
    elif command -v xdg-open >/dev/null 2>&1; then
        echo "Opening documentation in browser..."
        xdg-open docs/build/html/index.html
    else
        echo "Open docs/build/html/index.html in your browser to view the documentation."
    fi
else
    echo "Documentation generation failed. Check the error messages above."
fi