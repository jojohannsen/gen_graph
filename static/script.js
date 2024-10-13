let editor;

function initializeCodeMirror() {
    CodeMirror.defineSimpleMode("myDSL", {
        start: [
            { regex: /#.*/, token: "comment", sol: true },
            { regex: /(START)(\(.*\))(\s*=>\s*)([^\s]*)/, token: ["pale-pink", "magenta-bold", "arrow-cyan", "text-green"]},
            { regex: /^[^\s]+/, token: "left-margin-bold-green", sol: true },
            { regex: /([^\s]+)(\s*=>\s*)([^\s]+)/, token: ["left-margin-bold-green","text-green", "text-green"]},
            { regex: /(\s+[^\s]+)(\s*=>\s*)([^\s]+)/, token: ["text-blue","arrow-cyan", "text-green"]},
            { regex: /(\s+=>)(\s*[^\s]+)/, token: ["arrow-cyan", "text-green"]},
            { regex: /(\s+=>\s*)(.*)$/, token: ["arrow-cyan", "right-arrow-light-green"] }
        ]
    });

    const dslElement = document.getElementById('dsl');
    if (dslElement && !editor) {
        console.log("Creating editor from text area");
        editor = CodeMirror.fromTextArea(dslElement, {
            mode: "myDSL",
            lineNumbers: true,
            theme: "default",
            viewportMargin: Infinity
        });

        editor.on('change', function() {
            dslElement.value = editor.getValue();
        });

        window.editor = editor;  // Make the editor globally accessible
    }
}

function ensureEditorInitialized() {
    if (!window.editor) {
        initializeCodeMirror();
    }
}

function update_editor() {
    ensureEditorInitialized();
    if (window.editor) {
        const dslElement = document.getElementById('dsl');
        if (dslElement) {
            const newContent = dslElement.value;
            window.editor.setValue(newContent);
            window.editor.refresh();
        }
    } else {
        console.error("Failed to initialize editor");
    }
    
    // Trigger a refresh of the code generation UI
    htmx.trigger('#code-generation-ui', 'refreshContent');
}

// Initialize CodeMirror when the page loads
document.addEventListener('DOMContentLoaded', ensureEditorInitialized);

// Update editor after HTMX content swaps
document.body.addEventListener('htmx:afterSwap', update_editor);

// Refresh editor after HTMX settles
document.body.addEventListener('htmx:afterSettle', function(event) {
    ensureEditorInitialized();
    if (window.editor) window.editor.refresh();
});

// Add this function to update the selected example in the UI
function updateSelectedExample(architectureId) {
    const exampleLinks = document.querySelectorAll('.example-link');
    exampleLinks.forEach(link => {
        if (link.closest('div').querySelector('input[type="hidden"]').value === architectureId) {
            link.classList.add('selected');
        } else {
            link.classList.remove('selected');
        }
    });
}

// Update the architecture selection when changed
document.body.addEventListener('htmx:afterOnLoad', function(event) {
    if (event.detail.elt.id === 'examples-list') {
        const architectureId = document.getElementById('architecture_id').value;
        updateSelectedExample(architectureId);
    }
});
