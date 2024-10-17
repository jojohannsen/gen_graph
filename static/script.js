let editor;
let codeEditors = {};

function initializeCodeMirror(tabName = null) {
    if (!tabName) {
        CodeMirror.defineSimpleMode("myDSL", {
            start: [
                { regex: /#.*/, token: "comment", sol: true },
                { regex: /(START)(\(.*\))(\s*=>\s*)([^\s]*)/, token: ["pale-pink", "magenta-bold", "text-green", "text-green"]},
                { regex: /(\s+)(\w+\b\s*)(\s*=>\s*)([^\s]+.*)/, token: ["pale-pink", "text-blue", "arrow-cyan", "text-green"]},
                { regex: /(^\b[\w+,\s]+)(\s*=>\s*)([^\s]+.*)/, token: ["left-margin-bold-green","text-green", "text-green"]},
                { regex: /(\s+)(\s*=>\s*)([^\s]+.*)/, token: ["left-margin-bold-green","text-green", "text-green"]},
                { regex: /(^\b\w+\b\s*$)/, token: ["left-margin-bold-green"] }
            ]
        });

        const dslElement = document.getElementById('dsl');
        if (dslElement && !editor) {
            console.log("Creating DSL editor from text area");
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
    } else {
        const codeElement = document.getElementById(`${tabName}-code-editor`);
        if (codeElement) {
            console.log(`Setting up ${tabName} editor`);
            
            if (typeof CodeMirror.modes.python === 'undefined') {
                console.error('Python mode not available. Falling back to default mode.');
            }
            
            if (!codeEditors[tabName]) {
                // Create a new editor if it doesn't exist
                codeEditors[tabName] = CodeMirror.fromTextArea(codeElement, {
                    mode: typeof CodeMirror.modes.python !== 'undefined' ? "python" : "text",
                    lineNumbers: true,
                    theme: "default",
                    viewportMargin: Infinity,
                    lineWrapping: true,
                    minHeight: "300px",
                    indentUnit: 4,
                    tabSize: 4,
                    indentWithTabs: false,
                    autofocus: true
                });
            } else {
                // Refresh the existing editor
                codeEditors[tabName].toTextArea(); // Unwrap the editor
                codeEditors[tabName] = CodeMirror.fromTextArea(codeElement, {
                    mode: typeof CodeMirror.modes.python !== 'undefined' ? "python" : "text",
                    lineNumbers: true,
                    theme: "default",
                    viewportMargin: Infinity,
                    lineWrapping: true,
                    minHeight: "300px",
                    indentUnit: 4,
                    tabSize: 4,
                    indentWithTabs: false,
                    autofocus: true
                });
            }

            console.log(`${tabName} editor mode:`, codeEditors[tabName].getMode().name);

            codeEditors[tabName].setSize(null, "auto");  // Set height to auto

            codeEditors[tabName].on('change', function() {
                codeElement.value = codeEditors[tabName].getValue();
                codeEditors[tabName].setSize(null, "auto");  // Adjust height on change
            });
        } else {
            console.log(`${tabName} editor element not found`);
        }
    }
}

// Make sure initializeCodeMirror is globally accessible
window.initializeCodeMirror = initializeCodeMirror;

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
    
    // Initialize or refresh the code editors if they exist
    ['state', 'nodes', 'conditions', 'tools', 'data', 'llms'].forEach(tabName => {
        if (document.getElementById(`${tabName}-code-editor`)) {
            initializeCodeMirror(tabName);
            if (codeEditors[tabName]) {
                codeEditors[tabName].refresh();
                codeEditors[tabName].setSize(null, "auto");  // Adjust height
            }
        }
    });
    
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
    Object.values(codeEditors).forEach(editor => {
        if (editor) editor.refresh();
    });
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

function refreshCodeMirror() {
    if (window.editor) {
        console.log('Refreshing DSL CodeMirror editor');
        window.editor.refresh();
    }
    Object.values(codeEditors).forEach(editor => {
        if (editor) {
            console.log('Refreshing CodeMirror editor');
            editor.refresh();
        }
    });
}

// Add an event listener for tab changes
document.addEventListener('htmx:afterSettle', function(event) {
    if (event.detail.target.id === 'code-generation-ui') {
        console.log('Tab changed, refreshing CodeMirror');
        refreshCodeMirror();
    }
});