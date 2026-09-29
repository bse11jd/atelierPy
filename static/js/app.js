/**
 * Bascule l'affichage entre la vue "lecture" et la vue "édition" d'une ligne.
 * Utilisé sur les écrans Catégories, Catalogue, Paiement.
 */
function toggleEdition(id) {
    var vue = document.getElementById("vue-" + id);
    var edition = document.getElementById("edition-" + id);
    if (!vue || !edition) return;

    var enEdition = edition.style.display === "table-row";
    vue.style.display = enEdition ? "table-row" : "none";
    edition.style.display = enEdition ? "none" : "table-row";
}

/**
 * Bloque la navigation ailleurs sur le site (menu, logo, déconnexion, fermeture
 * d'onglet/actualisation) tant qu'une vente en caisse n'est pas finalisée
 * (Encaisser ou Enregistrer). Les formulaires de la page (ajout de prestation,
 * quantité, Encaisser, Enregistrer, Annuler) restent, eux, pleinement actifs :
 * seuls les liens de navigation générale sont interceptés.
 */
function bloquerNavigationVenteEnCours() {
    var message = "Merci de terminer cette vente (Encaisser, Enregistrer ou Annuler) avant de quitter cette page.";

    var liensABloquer = document.querySelectorAll(".menu a, .logo, .btn-logout");
    liensABloquer.forEach(function (lien) {
        lien.addEventListener("click", function (evenement) {
            evenement.preventDefault();
            window.alert(message);
        });
    });

    // Les formulaires DE CETTE PAGE (ajout de prestation, quantité, Encaisser,
    // Enregistrer, Annuler...) doivent pouvoir s'envoyer librement : on lève
    // l'alerte de fermeture juste avant leur soumission.
    document.querySelectorAll("form").forEach(function (formulaire) {
        formulaire.addEventListener("submit", function () {
            window.onbeforeunload = null;
        });
    });

    window.onbeforeunload = function () {
        return message;
    };
}

/**
 * Écran Caisse (détail d'un panier) : le nom de l'adhérent est saisi dans un
 * champ SÉPARÉ du bouton "Enregistrer" (il y a aussi les boutons de
 * prestation, la quantité, la suppression de ligne, "Encaisser"...), et
 * chacune de ces actions recharge la page. Sans cela, taper un nom puis
 * cliquer sur une prestation avant d'avoir cliqué "Enregistrer" faisait
 * disparaître la saisie.
 *
 * On intercepte donc TOUTE soumission de formulaire sur la page et on y
 * recopie la valeur courante du champ "Adhérent", pour que chaque action
 * transmette aussi le nom tapé au serveur (qui le mémorise sans exiger un
 * "Enregistrer" explicite - voir ROUTES/caisse.py, _memoriser_nom_adherent_saisi).
 */
document.addEventListener("submit", function (evenement) {
    var champ = document.getElementById("champ-nom-adherent");
    if (!champ) return; // pas sur l'écran de détail d'un panier

    var formulaire = evenement.target;
    if (formulaire.elements["nom_adherent"]) return; // déjà présent (formulaire "Enregistrer")

    var champCache = document.createElement("input");
    champCache.type = "hidden";
    champCache.name = "nom_adherent";
    champCache.value = champ.value;
    formulaire.appendChild(champCache);
});
