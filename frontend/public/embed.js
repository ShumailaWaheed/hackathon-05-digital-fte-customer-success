/**
 * T039: Iframe embed loader for third-party websites.
 *
 * Usage:
 *   <script src="https://your-domain.com/embed.js"
 *           data-src="https://your-domain.com"
 *           data-width="100%"
 *           data-height="600"></script>
 */
(function () {
  var script =
    document.currentScript ||
    document.querySelector('script[src*="embed.js"]');
  var src = script.getAttribute("data-src") || script.src.replace(/\/embed\.js.*$/, "");
  var width = script.getAttribute("data-width") || "100%";
  var height = script.getAttribute("data-height") || "600";

  var iframe = document.createElement("iframe");
  iframe.src = src;
  iframe.width = width;
  iframe.height = height + "px";
  iframe.style.border = "none";
  iframe.style.borderRadius = "8px";
  iframe.style.maxWidth = "640px";
  iframe.style.margin = "0 auto";
  iframe.style.display = "block";
  iframe.setAttribute("title", "Customer Support Form");
  iframe.setAttribute("loading", "lazy");

  script.parentNode.insertBefore(iframe, script.nextSibling);
})();
