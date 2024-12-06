let currentImageData = null;

// Auto-resize textarea
const textarea = document.getElementById('message-input');
textarea.addEventListener('input', function() {
    this.style.height = '28px';
    this.style.height = (this.scrollHeight) + 'px';
});

function appendMessage(content, isUser = false) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper';
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start space-x-4';
    
    // Avatar
    const avatarDiv = document.createElement('div');
    if (isUser) {
        avatarDiv.className = 'w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 font-bold text-sm';
        avatarDiv.textContent = 'You';
    } else {
        avatarDiv.className = 'w-8 h-8 rounded-full ai-avatar flex items-center justify-center text-white font-bold text-sm';
        avatarDiv.textContent = 'CE';
    }
    
    // Message content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'flex-1';
    
    const innerDiv = document.createElement('div');
    innerDiv.className = 'prose prose-slate max-w-none';
    
    if (!isUser && content) {
        try {
            innerDiv.innerHTML = marked.parse(content);
        } catch (e) {
            console.error('Error parsing markdown:', e);
            innerDiv.textContent = content;
        }
    } else {
        innerDiv.textContent = content || '';
    }
    
    contentDiv.appendChild(innerDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    messageWrapper.appendChild(messageDiv);
    messagesDiv.appendChild(messageWrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Event Listeners
document.getElementById('upload-btn').addEventListener('click', () => {
    document.getElementById('file-input').click();
});

document.getElementById('file-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.success) {
                currentImageData = data.image_data;
                document.getElementById('preview-img').src = `data:image/png;base64,${data.image_data}`;
                document.getElementById('image-preview').classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error uploading image:', error);
        }
    }
});

document.getElementById('remove-image').addEventListener('click', () => {
    currentImageData = null;
    document.getElementById('image-preview').classList.add('hidden');
    document.getElementById('file-input').value = '';
});

function appendThinkingIndicator() {
    const messagesDiv = document.getElementById('chat-messages');
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper thinking-message';
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start space-x-4';
    
    // AI Avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'w-8 h-8 rounded-full ai-avatar flex items-center justify-center text-white font-bold text-sm';
    avatarDiv.textContent = 'CE';
    
    // Thinking content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'flex-1';
    
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'thinking';
    thinkingDiv.innerHTML = 'Thinking<span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span>';
    
    contentDiv.appendChild(thinkingDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    messageWrapper.appendChild(messageDiv);
    messagesDiv.appendChild(messageWrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    return messageWrapper;
}

// Add command+enter handler
document.getElementById('message-input').addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('chat-form').dispatchEvent(new Event('submit'));
    }
});

// Add function to show tool usage
function appendToolUsage(toolName) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper';
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start space-x-4';
    
    // AI Avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'w-8 h-8 rounded-full ai-avatar flex items-center justify-center text-white font-bold text-sm';
    avatarDiv.textContent = 'CE';
    
    // Tool usage content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'flex-1';
    
    const toolDiv = document.createElement('div');
    toolDiv.className = 'tool-usage';
    toolDiv.textContent = `Using tool: ${toolName}`;
    
    contentDiv.appendChild(toolDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    messageWrapper.appendChild(messageDiv);
    messagesDiv.appendChild(messageWrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Update the chat form submit handler to handle tool usage
document.getElementById('chat-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message && !currentImageData) return;
    
    // Append user message
    appendMessage(message, true);
    
    // Clear input and reset height
    messageInput.value = '';
    resetTextarea();
    
    try {
        // Add thinking indicator
        const thinkingMessage = appendThinkingIndicator();
        
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message,
                image: currentImageData
            })
        });
        
        const data = await response.json();
        
        // Remove thinking indicator
        if (thinkingMessage) {
            thinkingMessage.remove();
        }
        
        // Show tool usage if present
        if (data.tool_name) {
            appendToolUsage(data.tool_name);
        }
        
        // Show response if we have one
        if (data && data.response) {
            appendMessage(data.response);
        } else {
            appendMessage('Error: No response received');
        }
        
        // Clear image after sending
        currentImageData = null;
        document.getElementById('image-preview').classList.add('hidden');
        document.getElementById('file-input').value = '';
        
    } catch (error) {
        console.error('Error sending message:', error);
        document.querySelector('.thinking-message')?.remove();
        appendMessage('Error: Failed to send message');
    }
});

function resetTextarea() {
    const textarea = document.getElementById('message-input');
    textarea.style.height = '28px';
}

document.getElementById('chat-form').addEventListener('reset', () => {
    resetTextarea();
});

// Add at the top of the file
window.addEventListener('load', async () => {
    try {
        // Reset the conversation when page loads
        const response = await fetch('/reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            console.error('Failed to reset conversation');
        }
        
        // Clear any existing messages except the first one
        const messagesDiv = document.getElementById('chat-messages');
        const messages = messagesDiv.getElementsByClassName('message-wrapper');
        while (messages.length > 1) {
            messages[1].remove();
        }
        
        // Reset any other state
        currentImageData = null;
        document.getElementById('image-preview')?.classList.add('hidden');
        document.getElementById('file-input').value = '';
        document.getElementById('message-input').value = '';
        resetTextarea();
        
    } catch (error) {
        console.error('Error resetting conversation:', error);
    }
}); 