for script in scripts/*.sh; do
    echo "===== Running $script ====="
    bash "$script" || { echo "FAILED: $script"; exit 1; }
done