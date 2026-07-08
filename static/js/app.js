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
