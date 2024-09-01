document.addEventListener('DOMContentLoaded', function() {
    var socket = io.connect('http://' + document.domain + ':' + location.port);

    var messageInput = document.getElementById('message-input');
    var chatMessages = document.getElementById('chat-messages');
    
    // Suponiendo que el nombre de usuario se obtiene de una variable global en el HTML
    var username = document.getElementById('username').textContent;

    window.sendMessage = function() {
        var message = messageInput.value;
        if (message) {
            socket.send({ user: username, text: message }); // Enviar el mensaje al servidor
            messageInput.value = ''; // Limpiar el campo de entrada
        }
    };

    socket.on('message', function(data) {
        var messageElement = document.createElement('div');
        messageElement.className = 'message';
        
        // Agregar la clase 'sent' si el mensaje es del usuario actual
        if (data.user === username) {
            messageElement.classList.add('sent');
        } else {
            messageElement.classList.add('received');
        }
        
        messageElement.innerHTML = `
            <div class="message-header">
                <strong>${data.user}</strong> <span>${new Date(data.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="message-body">
                ${data.text}
            </div>
        `;
        chatMessages.appendChild(messageElement); // Agregar el mensaje a la ventana de chat
        chatMessages.scrollTop = chatMessages.scrollHeight; // Desplazar hacia abajo automáticamente
    });

    // Agregar evento de clic al botón de enviar
    document.querySelector('.animated-btn').addEventListener('click', function() {
        sendMessage();
    });
});