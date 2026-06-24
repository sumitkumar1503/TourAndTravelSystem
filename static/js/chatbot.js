/* TravelGenie chatbot widget */
(function () {
    const root = document.getElementById('tg-chat-root');
    if (!root) return;

    const toggleBtn = document.getElementById('tg-chat-toggle');
    const closeBtn = document.getElementById('tg-chat-close');
    const win = document.getElementById('tg-chat-window');
    const msgs = document.getElementById('tg-chat-messages');
    const form = document.getElementById('tg-chat-form');
    const input = document.getElementById('tg-chat-text');
    const quickBtns = document.querySelectorAll('.tg-chat-quick .quick');

    function getCookie(name) {
        const v = document.cookie.split('; ').find(r => r.startsWith(name + '='));
        return v ? decodeURIComponent(v.split('=')[1]) : '';
    }

    function escapeHtml(s) {
        return String(s)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;');
    }

    // --- Allow safe inline HTML from server (b, i, em, br, code) ---
    function renderBotText(s) {
        const safe = escapeHtml(s)
            .replaceAll('&lt;b&gt;', '<b>').replaceAll('&lt;/b&gt;', '</b>')
            .replaceAll('&lt;i&gt;', '<i>').replaceAll('&lt;/i&gt;', '</i>')
            .replaceAll('&lt;em&gt;', '<em>').replaceAll('&lt;/em&gt;', '</em>')
            .replaceAll('&lt;code&gt;', '<code>').replaceAll('&lt;/code&gt;', '</code>')
            .replaceAll('\n', '<br>');
        return safe;
    }

    function appendUser(text) {
        const div = document.createElement('div');
        div.className = 'tg-msg user';
        div.textContent = text;
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
    }

    function appendBot(text) {
        const div = document.createElement('div');
        div.className = 'tg-msg bot';
        div.innerHTML = renderBotText(text);
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
    }

    function appendCards(cards) {
        cards.forEach(c => {
            const wrap = document.createElement('div');
            wrap.className = 'tg-card';

            if (c.type === 'flight') {
                wrap.innerHTML = `
                    <div class="ttl">${escapeHtml(c.title)}</div>
                    <div class="sub">${escapeHtml(c.subtitle)}</div>
                    <div class="sub">${escapeHtml(c.departure)} → ${escapeHtml(c.arrival)} · ${escapeHtml(c.duration)} · ${escapeHtml(c.cabin)}</div>
                    <div class="row">
                        <span class="price">₹${c.price.toLocaleString('en-IN')}</span>
                        <a class="book btn btn-sm btn-warning" href="${c.book_url}">Book</a>
                    </div>`;
            } else if (c.type === 'hotel') {
                const stars = '★'.repeat(c.stars);
                wrap.innerHTML = `
                    ${c.image ? `<div style="height:90px;background:url('${c.image}') center/cover;border-radius:8px;margin-bottom:6px;"></div>` : ''}
                    <div class="ttl">${escapeHtml(c.title)} <span class="text-warning">${stars}</span></div>
                    <div class="sub">${escapeHtml(c.subtitle)}</div>
                    <div class="sub">${(c.amenities || []).map(a => escapeHtml(a)).join(' · ')}</div>
                    <div class="row">
                        <span class="price">₹${c.price.toLocaleString('en-IN')}<small> /night</small></span>
                        <a class="book btn btn-sm btn-warning" href="${c.book_url}">Book</a>
                    </div>`;
            }
            msgs.appendChild(wrap);
        });
        msgs.scrollTop = msgs.scrollHeight;
    }

    function appendActions(actions) {
        if (!actions || !actions.length) return;
        const wrap = document.createElement('div');
        wrap.className = 'tg-msg bot';
        wrap.style.background = 'transparent';
        wrap.style.border = 'none';
        wrap.style.padding = '0';
        actions.forEach(a => {
            const link = document.createElement('a');
            link.className = 'tg-action-btn';
            link.href = a.url;
            link.textContent = a.label;
            wrap.appendChild(link);
        });
        msgs.appendChild(wrap);
        msgs.scrollTop = msgs.scrollHeight;
    }

    function appendTyping() {
        const div = document.createElement('div');
        div.className = 'tg-msg bot typing-indicator';
        div.id = 'tg-typing';
        div.innerHTML = '<span></span><span></span><span></span>';
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
    }
    function removeTyping() {
        const t = document.getElementById('tg-typing');
        if (t) t.remove();
    }

    async function sendMessage(text) {
        appendUser(text);
        appendTyping();
        try {
            const r = await fetch('/chatbot/api/message/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ message: text }),
                credentials: 'same-origin',
            });
            removeTyping();
            if (!r.ok) {
                appendBot("Hmm, something went wrong. Please try again.");
                return;
            }
            const data = await r.json();
            appendBot(data.reply || '...');
            if (data.cards && data.cards.length) appendCards(data.cards);
            if (data.actions && data.actions.length) appendActions(data.actions);
        } catch (err) {
            removeTyping();
            appendBot("Network error. Please check your connection.");
        }
    }

    function open() {
        win.hidden = false;
        if (!msgs.dataset.greeted) {
            msgs.dataset.greeted = '1';
            setTimeout(() => {
                appendBot("Hi! 👋 I'm <b>TravelGenie</b>, your AI travel assistant. How can I help today?\n\nTry: <em>flights from Delhi to Goa tomorrow</em> or <em>hotels in Manali for 3 nights</em>.");
            }, 200);
        }
        setTimeout(() => input.focus(), 250);
    }
    function close() { win.hidden = true; }

    toggleBtn.addEventListener('click', () => win.hidden ? open() : close());
    closeBtn.addEventListener('click', close);

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;
        input.value = '';
        sendMessage(text);
    });

    quickBtns.forEach(b => b.addEventListener('click', () => {
        sendMessage(b.dataset.q);
    }));

    // -------- Voice input via Web Speech API --------
    const voiceBtn = document.getElementById('tg-chat-voice');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (voiceBtn) {
        if (!SpeechRecognition) {
            voiceBtn.title = "Voice input unavailable in this browser";
            voiceBtn.classList.add('opacity-50');
            voiceBtn.disabled = true;
        } else {
            const recog = new SpeechRecognition();
            recog.lang = 'en-IN';
            recog.continuous = false;
            recog.interimResults = false;
            let listening = false;

            voiceBtn.addEventListener('click', () => {
                if (listening) { recog.stop(); return; }
                try {
                    recog.start();
                    listening = true;
                    voiceBtn.classList.add('btn-danger');
                    voiceBtn.classList.remove('btn-outline-secondary');
                    voiceBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
                    input.placeholder = 'Listening...';
                } catch (e) { /* ignore */ }
            });
            recog.onresult = (ev) => {
                const t = ev.results[0][0].transcript;
                input.value = t;
                sendMessage(t);
                input.value = '';
            };
            recog.onerror = () => { /* swallow */ };
            recog.onend = () => {
                listening = false;
                voiceBtn.classList.remove('btn-danger');
                voiceBtn.classList.add('btn-outline-secondary');
                voiceBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
                input.placeholder = 'Type or speak your message...';
            };
        }
    }

    // Public API for external triggers
    window.TravelGenieChat = { open, close, send: sendMessage };
})();
