/* Poprawki enigmalabz.com, 22.10.2026. Nakładka na zbudowaną stronę – przy buildzie ze źródeł przenieść do komponentu hero.
   Desktop: „3,2× szybciej” stoi dokładnie pod przyciskiem „Sprawdź swoją kartę”, niezależnie od wysokości okna. */
(function () {
  "use strict";
  var ODSTEP = 18; // px między dołem przycisku a górą „3,2×”

  // pozycja względem sekcji hero liczona z offsetTop – nie zależy od animacji transform w hero
  function gora(el, hero) {
    var y = 0;
    while (el && el !== hero) { y += el.offsetTop; el = el.offsetParent; }
    return y;
  }

  function ustaw() {
    var hero = document.querySelector("section.hero");
    if (!hero) return;
    var akcje = hero.querySelector(".actions");
    var srodek = hero.querySelector(".near .center");
    if (!akcje || !srodek) return;
    var kolumny = getComputedStyle(srodek.parentElement).gridTemplateColumns.split(" ").length;
    if (kolumny !== 5) { srodek.style.translate = ""; return; } // układ mobilny zostaje bez zmian
    var przesun = gora(akcje, hero) + akcje.offsetHeight + ODSTEP - gora(srodek, hero);
    srodek.style.translate = "0 " + Math.round(przesun) + "px";
  }

  var czeka = 0;
  function pozniej() { cancelAnimationFrame(czeka); czeka = requestAnimationFrame(ustaw); }

  addEventListener("resize", pozniej, { passive: true });
  addEventListener("load", pozniej);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(pozniej);
  // SvelteKit podmienia treść przy przejściach bez przeładowania – pilnujemy nowego hero
  new MutationObserver(pozniej).observe(document.body, { childList: true, subtree: true });
  pozniej();
})();
