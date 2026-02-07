#!/bin/sh
# shellcheck shell=sh
# Interactive shell configuration reviewer and editor for tokentap

set -e

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/common.sh
. "$SCRIPT_DIR/common.sh"

# Color codes for highlighting
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Get shell RC file
SHELL_RC=$(get_shell_rc)

# Backup shell RC
backup_shell_rc() {
    local backup_file="${SHELL_RC}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$SHELL_RC" "$backup_file"
    log_success "Backup created: $backup_file"
}

# Show current tokentap integration
show_current_integration() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Current Tokentap Integration in $SHELL_RC"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if grep -q "tokentap" "$SHELL_RC" 2>/dev/null; then
        log_info "Found tokentap configuration:"
        echo ""
        grep -n "tokentap" "$SHELL_RC" | while IFS=: read -r line_num content; do
            printf "${DIM}%3d${NC} | %s\n" "$line_num" "$content"
        done
    else
        log_warn "No tokentap configuration found"
    fi
    echo ""
}

# Show recommended configuration
show_recommended_config() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Recommended Tokentap Configuration"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    cat <<'EOF'
# >>> tokentap shell integration >>>
# Auto-configured proxy environment for LLM token tracking
if command -v tokentap &> /dev/null; then
  eval "$(tokentap shell-init)"
fi
# <<< tokentap shell integration <<<

# Tokentap convenience aliases
alias tokentap-start='tokentap up && echo "✓ Tokentap proxy and services started"'
alias tokentap-stop='tokentap down && echo "✓ Tokentap services stopped"'
alias tokentap-web-start='docker start tokentap-client-web-1 2>/dev/null && echo "✓ Tokentap web dashboard started at http://127.0.0.1:3000" || echo "✗ Failed to start web dashboard"'
alias tokentap-web-stop='docker stop tokentap-client-web-1 2>/dev/null && echo "✓ Tokentap web dashboard stopped" || echo "✗ Web dashboard not running"'
alias tokentap-status='tokentap status'
alias tokentap-logs='tokentap logs'
alias tokentap-open='tokentap open'
EOF

    echo ""
}

# Analyze current shell RC
analyze_shell_rc() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Shell Configuration Analysis"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    local issues=0

    # Check for tokentap shell-init
    if grep -q "tokentap shell-init" "$SHELL_RC" 2>/dev/null; then
        log_success "Shell integration present"
    else
        log_warn "Shell integration missing"
        issues=$((issues + 1))
    fi

    # Check for aliases
    if grep -q "tokentap-start" "$SHELL_RC" 2>/dev/null; then
        log_success "Convenience aliases present"
    else
        log_warn "Convenience aliases missing"
        issues=$((issues + 1))
    fi

    # Check for conflicts
    if grep -q "HTTPS_PROXY.*=" "$SHELL_RC" 2>/dev/null | grep -v "tokentap" >/dev/null 2>&1; then
        log_warn "Found other HTTPS_PROXY configuration (may conflict)"
        echo "       Lines:"
        grep -n "HTTPS_PROXY.*=" "$SHELL_RC" | grep -v "tokentap" | while IFS=: read -r line_num content; do
            printf "       ${DIM}%3d${NC} | %s\n" "$line_num" "$content"
        done
        issues=$((issues + 1))
    fi

    # Check placement (should be near end, after kiro-cli post block if present)
    if grep -q "kiro-cli.*post" "$SHELL_RC" 2>/dev/null; then
        local kiro_line
        kiro_line=$(grep -n "kiro-cli.*post" "$SHELL_RC" | tail -1 | cut -d: -f1)
        local tokentap_line
        tokentap_line=$(grep -n "tokentap shell-init" "$SHELL_RC" | tail -1 | cut -d: -f1)

        if [ -n "$tokentap_line" ] && [ "$tokentap_line" -lt "$kiro_line" ]; then
            log_warn "Tokentap integration is before Kiro CLI post block"
            echo "       Should be after line $kiro_line"
            issues=$((issues + 1))
        else
            log_success "Integration properly placed after Kiro CLI"
        fi
    fi

    echo ""
    if [ $issues -eq 0 ]; then
        log_success "No issues found!"
    else
        log_info "Found $issues potential issue(s)"
    fi

    return $issues
}

# Interactive menu
show_menu() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  What would you like to do?"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  1) View current integration"
    echo "  2) View recommended configuration"
    echo "  3) Analyze configuration"
    echo "  4) Add/update shell integration"
    echo "  5) Add convenience aliases"
    echo "  6) Remove all tokentap configuration"
    echo "  7) Create backup"
    echo "  8) Open $SHELL_RC in editor"
    echo "  9) Exit"
    echo ""
    printf "Select option [1-9]: "
}

# Add or update shell integration
add_shell_integration() {
    backup_shell_rc

    log_info "Adding/updating shell integration..."

    # Remove old integration if present
    if grep -q "tokentap shell-init" "$SHELL_RC" 2>/dev/null; then
        sed -i.tmp '/>>> tokentap shell integration >>>/,/<<< tokentap shell integration <<</d' "$SHELL_RC"
        rm -f "$SHELL_RC.tmp"
        log_info "Removed old integration"
    fi

    # Add new integration at the end (or after kiro-cli post block)
    if grep -q "kiro-cli.*post" "$SHELL_RC" 2>/dev/null; then
        # Insert after kiro-cli post block
        local insert_line
        insert_line=$(grep -n "kiro-cli.*post" "$SHELL_RC" | tail -1 | cut -d: -f1)
        insert_line=$((insert_line + 1))

        # Use awk to insert at specific line
        awk -v n="$insert_line" -v text="
# >>> tokentap shell integration >>>
if command -v tokentap &> /dev/null; then
  eval \"\$(tokentap shell-init)\"
fi
# <<< tokentap shell integration <<<
" 'NR==n{print text}1' "$SHELL_RC" > "$SHELL_RC.tmp"
        mv "$SHELL_RC.tmp" "$SHELL_RC"
        log_success "Shell integration added after Kiro CLI"
    else
        # Append to end
        cat >> "$SHELL_RC" <<'EOF'

# >>> tokentap shell integration >>>
if command -v tokentap &> /dev/null; then
  eval "$(tokentap shell-init)"
fi
# <<< tokentap shell integration <<<
EOF
        log_success "Shell integration added to end of file"
    fi

    echo ""
    log_info "Reload your shell: source $SHELL_RC"
}

# Add convenience aliases
add_aliases() {
    backup_shell_rc

    log_info "Adding convenience aliases..."

    # Check if already present
    if grep -q "tokentap-start" "$SHELL_RC" 2>/dev/null; then
        log_warn "Aliases already present, updating..."
        sed -i.tmp '/# Tokentap convenience aliases/,/^$/d' "$SHELL_RC"
        rm -f "$SHELL_RC.tmp"
    fi

    # Add aliases after shell integration
    if grep -q "tokentap shell-init" "$SHELL_RC" 2>/dev/null; then
        local insert_line
        insert_line=$(grep -n "<<< tokentap shell integration <<<" "$SHELL_RC" | tail -1 | cut -d: -f1)
        insert_line=$((insert_line + 1))

        awk -v n="$insert_line" -v text="
# Tokentap convenience aliases
alias tokentap-start='tokentap up && echo \"✓ Tokentap proxy and services started\"'
alias tokentap-stop='tokentap down && echo \"✓ Tokentap services stopped\"'
alias tokentap-web-start='docker start tokentap-client-web-1 2>/dev/null && echo \"✓ Tokentap web dashboard started at http://127.0.0.1:3000\" || echo \"✗ Failed to start web dashboard\"'
alias tokentap-web-stop='docker stop tokentap-client-web-1 2>/dev/null && echo \"✓ Tokentap web dashboard stopped\" || echo \"✗ Web dashboard not running\"'
alias tokentap-status='tokentap status'
alias tokentap-logs='tokentap logs'
alias tokentap-open='tokentap open'
" 'NR==n{print text}1' "$SHELL_RC" > "$SHELL_RC.tmp"
        mv "$SHELL_RC.tmp" "$SHELL_RC"
        log_success "Aliases added after shell integration"
    else
        # Append to end if no integration found
        cat >> "$SHELL_RC" <<'EOF'

# Tokentap convenience aliases
alias tokentap-start='tokentap up && echo "✓ Tokentap proxy and services started"'
alias tokentap-stop='tokentap down && echo "✓ Tokentap services stopped"'
alias tokentap-web-start='docker start tokentap-client-web-1 2>/dev/null && echo "✓ Tokentap web dashboard started at http://127.0.0.1:3000" || echo "✗ Failed to start web dashboard"'
alias tokentap-web-stop='docker stop tokentap-client-web-1 2>/dev/null && echo "✓ Tokentap web dashboard stopped" || echo "✗ Web dashboard not running"'
alias tokentap-status='tokentap status'
alias tokentap-logs='tokentap logs'
alias tokentap-open='tokentap open'
EOF
        log_success "Aliases added to end of file"
    fi

    echo ""
    log_info "Reload your shell: source $SHELL_RC"
}

# Remove all tokentap configuration
remove_all() {
    backup_shell_rc

    log_info "Removing all tokentap configuration..."

    # Remove shell integration
    if grep -q "tokentap shell-init" "$SHELL_RC" 2>/dev/null; then
        sed -i.tmp '/>>> tokentap shell integration >>>/,/<<< tokentap shell integration <<</d' "$SHELL_RC"
        rm -f "$SHELL_RC.tmp"
        log_info "Removed shell integration"
    fi

    # Remove aliases
    if grep -q "# Tokentap convenience aliases" "$SHELL_RC" 2>/dev/null; then
        sed -i.tmp '/# Tokentap convenience aliases/,/tokentap-open/d' "$SHELL_RC"
        rm -f "$SHELL_RC.tmp"
        log_info "Removed aliases"
    fi

    # Clean up extra blank lines
    sed -i.tmp '/^$/N;/^\n$/d' "$SHELL_RC"
    rm -f "$SHELL_RC.tmp"

    log_success "All tokentap configuration removed"
    echo ""
    log_info "Reload your shell: source $SHELL_RC"
}

# Open in editor
open_editor() {
    local editor="${EDITOR:-nano}"
    log_info "Opening $SHELL_RC in $editor..."
    "$editor" "$SHELL_RC"
}

# Main interactive loop
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Tokentap Shell Configuration Review"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    log_info "Shell RC file: $SHELL_RC"

    while true; do
        show_menu
        read -r choice

        case "$choice" in
            1)
                show_current_integration
                ;;
            2)
                show_recommended_config
                ;;
            3)
                analyze_shell_rc
                ;;
            4)
                add_shell_integration
                ;;
            5)
                add_aliases
                ;;
            6)
                printf "\nAre you sure you want to remove all tokentap configuration? [y/N] "
                read -r confirm
                if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                    remove_all
                else
                    log_info "Cancelled"
                fi
                ;;
            7)
                backup_shell_rc
                ;;
            8)
                open_editor
                ;;
            9)
                echo ""
                log_info "Goodbye!"
                echo ""
                exit 0
                ;;
            *)
                log_error "Invalid option: $choice"
                ;;
        esac

        echo ""
        printf "Press Enter to continue..."
        read -r _
    done
}

main "$@"
