(function () {
    const url = window.location.href;
    if (url.match(/(https:\/\/)(.*)(\.udemy.com\/course\/)(.*)(\/learn\/)(.*)(\/)(\d+)(.*)/g)) {
        try {
            const token = document.cookie.split(";").filter(e => e.includes("access_token"))[0].split("=")[1];
            const clientId = document.cookie.split(";").filter(e => e.includes("client_id"))[0].split("=")[1];
            console.log(`token: ${token}\nclient id: ${clientId}`)
        } catch (err) {
            alert('Make sure that you are logged in!')
        }
    } else {
        alert('This is not an Udemy course page!')
    }
})();