CodeMirror.defineSimpleMode("myDSL", {
    start: [
        // Match lines starting with non-whitespace, text on the left margin is bold and green
        { regex: /(START)(\(.*\))(\s*=>\s*)([^\s]*)/, token: ["pale-pink", "magenta-bold", "arrow-cyan", "text-green"]},
        { regex: /^[^\s]+/, token: "left-margin-bold-green", sol: true },
        // Match '=>' when the line starts with whitespace, color left text blue, arrow cyan
        { regex: /([^\s]+)(\s*=>\s*)([^\s]+)/, token: ["left-margin-bold-green","text-green", "text-green"]},
        { regex: /(\s+[^\s]+)(\s*=>\s*)([^\s]+)/, token: ["text-blue","arrow-cyan", "text-green"]},
        { regex: /(\s+=>)(\s*[^\s]+)/, token: ["arrow-cyan", "text-green"]},
        // Match text after '=>' and apply bold light green styling
        { regex: /(\s+=>\s*)(.*)$/, token: ["arrow-cyan", "right-arrow-light-green"] }
    ]
});


console.log("Creating editor from text area");
let editor = CodeMirror.fromTextArea(document.getElementById('dsl'), {
    mode: "myDSL",
    lineNumbers: true,
    theme: "default",
    viewportMargin: Infinity // This allows the editor to expand to its container's height
});

// Remove the setEditorHeight function and the resize event listener

function update_editor() {
    console.log("update_editor");
    // Get the new content from the textarea
    const newContent = document.getElementById('dsl').value;
    console.log("WE GOT NEW CONTENT");
    console.log(newContent);
    // Update the existing editor's content
    editor.setValue(newContent);
    editor.setSize(null, "600px"); 
    // Refresh the editor to ensure proper rendering
    editor.refresh();
}

// Call update_editor once when the page loads
//document.addEventListener('DOMContentLoaded', update_editor);