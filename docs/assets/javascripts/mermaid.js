// Zensical draws diagrams with a global mermaid. A module runs once a page, so
// coming back to a diagram doesn't bring a second, unconfigured copy.
import mermaid from "./mermaid/mermaid.esm.min.mjs";

window.mermaid = mermaid;
