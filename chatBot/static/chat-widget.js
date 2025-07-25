(function() {
  document.head.insertAdjacentHTML('beforeend', '<link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.16/tailwind.min.css" rel="stylesheet">');

  // Inject the CSS
  const style = document.createElement('style');
  style.innerHTML = `
  .hidden {
    display: none;
  }

  /* Global */
  html{
  min-height: 100%;
  overflow: hidden;
  }

  body{
  height: calc(100vh - 8em);
  padding: 4em;
  color: rgba(0, 0, 0, 0.75);
  font-family: 'Anonymous Pro', monospace;  
  background-color: rgb(25,25,25);  
  }

  .line-1{
      position: relative;
      top: 50%;  
      width: 35ch;
      margin: 0 auto;
      border-right: 2px solid rgba(0, 0, 0, 0.75);
      font-size: 180%;
      text-align: center;
      white-space: nowrap;
      overflow: hidden;
      transform: translateY(-50%);    
  }

  /* Animation */
  .anim-typewriter{
  animation: typewriter 4s steps(35) 1s 1 normal both,
              blinkTextCursor 500ms steps(35) infinite normal;
  }

  @keyframes typewriter{
  from{width: 0;}
  to{width: 35ch;}
  }

  @keyframes blinkTextCursor{
  from{border-right-color: rgba(0, 0, 0, 0.75);}
  to{border-right-color: transparent;}
  }
  
  #chat-widget-container {
    position: fixed;
    bottom: 20px;
    right: 20px;
    flex-direction: column;

  }
  
    
  #chat-popup {
    height: 70vh;
    max-height: 70vh;
    transition: all 0.3s;
    overflow: hidden;
  }
  @media (max-width: 768px) {
    #chat-popup {
      position: fixed;
      top: 0;
      right: 0;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 100%;
      max-height: 100%;
      border-radius: 0;
    }
  }

  `;

  document.head.appendChild(style);

  // Create chat widget container
  const chatWidgetContainer = document.createElement('div');
  chatWidgetContainer.id = 'chat-widget-container';
  document.body.appendChild(chatWidgetContainer);
  
  // Inject the HTML
  chatWidgetContainer.innerHTML = `
    <div id="chat-bubble" class="trans w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center cursor-pointer text-3xl">
      <svg id="chat-icon" xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
      <!-- Close Icon -->
      <svg id="close-icon" xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 text-white hidden" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </div>
    <div id="chat-popup" class="hidden absolute bottom-20 right-0 w-96 bg-white rounded-md shadow-md flex flex-col transition-all text-sm ">
      <div id="chat-header" class="flex justify-between items-center p-4 bg-gray-800 text-white rounded-t-md">
        <h3 class="m-0 text-lg">ChatBot Widget</h3>
        <button id="close-popup" class="bg-transparent border-none text-white cursor-pointer">
        </button>
      </div>
      <div id="chat-messages" class="flex-1 p-4 overflow-y-auto"></div>
      <div id="chat-input-container" class="p-4 border-t border-gray-200">
        <div class="flex space-x-4 items-center">
          <input type="text" id="chat-input" class="flex-1 border border-gray-300 rounded-md px-4 py-2 outline-none w-3/4" placeholder="Type your message...">
          <button id="chat-submit" class="bg-gray-800 text-white rounded-md px-4 py-2 cursor-pointer">Send</button>
        </div>
        <div class="flex text-center text-xs pt-4">
          <span class="flex-1">Created by <a href = "https://github.com/dqnyb" class = "text-blue-800" style = "color = #3b5998 !important">Daniel Brînza</span>
        </div>
      </div>
    </div>
  `;

  // Add event listeners
  const chatInput = document.getElementById('chat-input');
  const chatSubmit = document.getElementById('chat-submit');
  const chatMessages = document.getElementById('chat-messages');
  const chatBubble = document.getElementById('chat-bubble');
  const chatPopup = document.getElementById('chat-popup');
  const closePopup = document.getElementById('close-popup');
  const chatIcon = document.getElementById("chat-icon");
  const closeIcon = document.getElementById("close-icon");
  // const urlParams = new URLSearchParams(window.location.search);
  // const stepFromURL = urlParams.get("step");
  // let onboardingStep = 0;
  // if (stepFromURL === "feedback") {
  //   onboardingStep = 99; // sau alt cod liber dedicat pentru feedback
  //   console.log("onboardingStep = ", onboardingStep)
  // }

  chatBubble.addEventListener("click", () => {
    const isOpen = !chatPopup.classList.contains("hidden");
  
    // chatPopup.classList.toggle("hidden");
    chatIcon.classList.toggle("hidden");
    closeIcon.classList.toggle("hidden");
  });
  
  closePopup.addEventListener("click", () => {
    chatPopup.classList.add("hidden");
    chatIcon.classList.remove("hidden");
    closeIcon.classList.add("hidden");
  });

  function displayBotReply(text) {
      const messageElement = document.createElement('div');
      messageElement.className = 'flex mb-3';
      messageElement.innerHTML = `
        <div class="bg-gray-200 text-black rounded-lg py-2 px-4 max-w-[70%]">
          ${text}
        </div>
      `;
      chatMessages.appendChild(messageElement);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    

  chatSubmit.addEventListener('click', function() {
    
    const message = chatInput.value.trim();
    if (!message) return;
    
    chatMessages.scrollTop = chatMessages.scrollHeight;

    chatInput.value = '';

    onUserRequest(message);

  });

  chatInput.addEventListener('keyup', function(event) {
    if (event.key === 'Enter') {
      chatSubmit.click();
    }
  });

  chatBubble.addEventListener('click', function() {
    togglePopup();
  });

  closePopup.addEventListener('click', function() {
    togglePopup();
  });

  function togglePopup() {
    
      chatPopup.classList.toggle('hidden');
      chatPopup.classList.toggle('fullscreen');
      if (!chatPopup.classList.contains('hidden')) {
          document.body.classList.add('chat-open');
        chatInput.focus();
        if (window.onboardingStep === 99) {
          onboardingStep = 99;
        }
        
        if (onboardingStep === 99) {
          // Afișăm direct mesajul și formularul
          const replyElement = document.createElement('div');
          replyElement.className = 'flex mb-3';
          replyElement.innerHTML = `
            <div class="bg-gray-200 text-black rounded-lg py-2 px-4 max-w-[70%]">
              🎉 Salut! Proiectul tău a fost finalizat cu succes.<br>📝 Ne-ar ajuta mult feedbackul tău. Cât de mulțumit ai fost de colaborare?
            </div>
          `;
          chatMessages.appendChild(replyElement);
          chatMessages.scrollTop = chatMessages.scrollHeight;

          const feedbackForm = document.createElement('div');
          feedbackForm.className = "p-4 border rounded-xl bg-gray-100 mt-3 w-full";
        
          feedbackForm.innerHTML = `
            <div class="mb-2">
              <label class="font-medium">Alege un rating:</label>
              <div id="star-rating" class="flex space-x-1 mt-1">
                ${[1,2,3,4,5].map(i => `<span class="star text-2xl cursor-pointer text-gray-400" data-value="${i}">★</span>`).join('')}
              </div>
            </div>
            <textarea id="feedback-comment" placeholder="Lasă un comentariu..." rows="3" class="w-full p-2 rounded border"></textarea>
            <br/>
            <button id="send-feedback-btn" class="mt-2 px-4 py-2 rounded bg-blue-500 text-white hover:bg-blue-600">Trimite Feedback</button>
          `;
        
          chatMessages.appendChild(feedbackForm);
          chatMessages.scrollTop = chatMessages.scrollHeight;
        
          // ⭐ Funcționalitate stele interactive
          const stars = feedbackForm.querySelectorAll('.star');
          let selectedRating = 5;
        
          stars.forEach(star => {
            star.addEventListener('click', () => {
              selectedRating = parseInt(star.dataset.value);
              stars.forEach(s => {
                s.classList.toggle('text-yellow-400', parseInt(s.dataset.value) <= selectedRating);
                s.classList.toggle('text-gray-400', parseInt(s.dataset.value) > selectedRating);
              });
            });
          });
        
          // Butonul de trimitere
          document.getElementById('send-feedback-btn').addEventListener('click', () => {
            const comment = document.getElementById("feedback-comment").value;
        
            fetch("https://digital-52rr.onrender.com/feedback", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                rating: selectedRating,
                comment: comment,
                name: userName || "anonim"
              })
            })
            .then(res => res.json())
            .then(data => {
              // Adaugi spacerul ÎNAINTE de mesajul cu "Mulțumim"
              const spacer = document.createElement('div');
              spacer.className = "h-3 w-full block";  // sau: spacer.style.height = "24px";
              chatMessages.appendChild(spacer);

              // Apoi adaugi mesajul de mulțumire
              const replyElement = document.createElement('div');
              replyElement.className = 'flex mb-3';
              replyElement.innerHTML = `
                <div class="bg-gray-200 text-black rounded-lg py-2 px-4 max-w-[70%]">
                  ✅ Mulțumim mult pentru feedback! 🤗
                </div>
              `;
              chatMessages.appendChild(replyElement);

              chatMessages.scrollTop = chatMessages.scrollHeight;
            })
            .catch(err => {
              reply("❌ Eroare la trimitere: " + err.message);
            });
          });
        
          return;
        }

        if (chatMessages.children.length === 0 && onboardingStep === 0) {
          const typingElement = document.createElement('div');
          typingElement.className = 'flex mb-3';
          typingElement.id = 'typing-indicator';
          typingElement.innerHTML = `
            <div class="typing-dots flex space-x-2 px-4 py-2">
              <span class="dot w-3 h-3 bg-blue-600 rounded-full animate-bounce delay-0"></span>
              <span class="dot w-3 h-3 bg-blue-600 rounded-full animate-bounce delay-150"></span>
              <span class="dot w-3 h-3 bg-blue-600 rounded-full animate-bounce delay-300"></span>
            </div>
          `;
          chatMessages.appendChild(typingElement);
          chatMessages.scrollTop = chatMessages.scrollHeight;

          fetch("https://digital-52rr.onrender.com/start")
            .then(res => res.json())
            .then(data => {
              setTimeout(() => {
                typingElement.remove();
                displayBotReply(data.ask_name);
                console.log("onboardingStep  ========= = ", onboardingStep)
                onboardingStep = 1;
              }, 1000); // Delay de simulare typing
            });
        }
      } else {
          document.body.classList.remove('chat-open');
      }
    }

  let userName = null;
  let userInterests = null;
  let onboardingStep = 0;  // 0 = numele, 1 = interesele, 2 = chat-ul propriu-zis


    


  function onUserRequest(message) {
      const messageElement = document.createElement('div');
      messageElement.className = 'flex justify-end mb-3';
      messageElement.innerHTML = `
        <div class="bg-gray-800 text-white rounded-lg py-2 px-4 max-w-[70%]">
          ${message}
        </div>
      `;
      chatMessages.appendChild(messageElement);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    
      if (onboardingStep === 1) {
        userName = message;
        // onboardingStep = 2;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/interests", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              displayBotReply(data.ask_interests); // răspunsul real după delay
              if(data.ask_interests.includes("Mǎ bucur că vrei să plasezi o comandă!")){
                onboardingStep = 15;
                return;
              }
              if(data.ask_interests.includes("Landing Page One-Page") || data.ask_interests.includes("Site Simplu (3–5 pagini)")){
                onboardingStep = 2;
                return;
              } else if(data.ask_interests.includes("Te rugăm să ne spui dacă")){
                onboardingStep = 1;
                return;
              } else if (data.ask_interests.includes("📌 Cum ai dori să continuăm?")){
                onboardingStep = 4;
                return;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            displayBotReply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }
      
      if (onboardingStep === 4) {
        userName = message;
        // onboardingStep = 2;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/criteria", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              displayBotReply(data.message); // răspunsul real după delay
              if(data.message.includes("Landing Page One-Page") || data.message.includes("Site Simplu (3–5 pagini)")){
                onboardingStep = 2;
              } else if (data.message.includes("Haide să alegem un buget")){
                onboardingStep = 5;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            displayBotReply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }        
          
      if (onboardingStep === 2) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/welcome", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if(data.message.includes("Dacă vrei detalii despre ")){
                onboardingStep = 3;
              } else if(data.message.includes("Landing Page One-Page") || data.message.includes("Site Simplu (3–5 pagini)")){
                onboardingStep = 2;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }
      
      if (onboardingStep === 3) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay

              if (data.message.includes("Doriți să plasați o comandă pentru produsul")){
                onboardingStep = 20;
                return;
              }
              if(data.message.includes("Mǎ bucur că vrei să plasezi o comandă!")){
                onboardingStep = 15;
                return;
              }
              if(data.message.includes("Landing Page One-Page") || data.message.includes("Site Simplu (3–5 pagini)")){
                onboardingStep = 2;
              } else if(data.message.includes("Îți pot oferi o gamă variată de servicii IT specializate.")){
                onboardingStep = 2;
              } else if (data.message.includes("Haide să alegem un buget")){
                onboardingStep = 5;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      if (onboardingStep === 5) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/budget", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Apropo, ca să pot veni cu sugestii potrivite")){
                onboardingStep = 5;
              } else {
                onboardingStep = 6;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      if (onboardingStep === 6) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/preference_language", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Ca să-ți ofer informațiile cât mai potrivit")){
                onboardingStep = 6;
              } else {
                onboardingStep = 7;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      if (onboardingStep === 7) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/functionalities", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("❗️ Din ce ai scris, nu am reușit")){
                onboardingStep = 7;
              } else if (data.message.includes("Dorești să faci o comandă")){
                onboardingStep = 8;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }


      if (onboardingStep === 8) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/comanda", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Alegeți unul dintre următoarele produse pentru a plasa o comandă")){
                onboardingStep = 21;
                return;
              }
              if (data.message.includes("Dacă vrei detalii despre")){
                onboardingStep = 1;
              } else if (data.message.includes("Nu mi-e clar dacă vrei")){
                onboardingStep = 8;
              } else {
                onboardingStep = 12;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      if (onboardingStep === 9) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/ai_mai_comandat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Ne bucurăm să te avem din nou alături")){
                onboardingStep = 10;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      if (onboardingStep === 10) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/check_name_surname", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Mulțumim! Ai un nume frumos!")){
                onboardingStep = 11;
              } else if (data.message.includes("Introdu, te rog")){
                onboardingStep = 10;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      if (onboardingStep === 11) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/numar_de_telefon", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Numărul tău a fost salvat cu succes!")){
                onboardingStep = 14;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      if (onboardingStep === 12) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/afiseaza_produs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Iată toate detaliile despre")){
                onboardingStep = 13;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      if (onboardingStep === 13) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/confirma_produs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Landing Page One-Page") || data.message.includes("Site Simplu (3–5 pagini)")){
                onboardingStep = 12;
              } else if (data.message.includes("Serviciul a fost salvat cu succes")){
                onboardingStep = 10;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      if (onboardingStep === 14) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Am notat toate datele importante și totul este pregătit.")){
                onboardingStep = 1;
              } else {
                onboardingStep = 14;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }


      if (onboardingStep === 15) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/comanda_inceput", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Iată toate detaliile despre")){
                onboardingStep = 13;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      if (onboardingStep === 20) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/produs_intrebare", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Serviciul a fost salvat cu succes!")){
                onboardingStep = 10;
                return;
              }
              if (data.message.includes("Landing Page One-Page") || data.message.includes("Site Simplu (3–5 pagini)")){
                  onboardingStep = 12;
                  return;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }

      // https://digital-52rr.onrender.com

      if (onboardingStep === 21) {
        userInterests = message;
        // onboardingStep = 3;
      
        const typingElement = document.createElement('div');
        typingElement.className = 'flex mb-3';
        typingElement.id = 'typing-indicator';
        typingElement.innerHTML = `
          <div class="typing-dots flex space-x-2 px-4 py-2">
            <span class=""></span>
            <span class=""></span>
            <span class=""></span>
          </div>
        `;
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      
        fetch("https://digital-52rr.onrender.com/selecteaza_produs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: userName, interests: userInterests , message: message })
        })
          .then(res => res.json())
          .then(data => {
            setTimeout(() => {
              typingElement.remove();
              reply(data.message); // Afișează mesajul de bun venit după delay
              if (data.message.includes("Serviciul a fost salvat cu succes!")){
                onboardingStep = 10;
              }
            }, 1000);
          })
          .catch(err => {
            typingElement.remove();
            reply("Eroare la inițializare: " + err.message);
          });
      
        return;
      }




      // Chat normal
      fetch("https://digital-52rr.onrender.com/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
      })
      .then(res => res.json())
      .then(data => reply(data.reply))
      .catch(err => reply("A apărut o eroare: " + err.message));
    }      
  
    function reply(message) {

      const chatMessages = document.getElementById('chat-messages');
    
      const typingElement = document.createElement('div');
      typingElement.className = 'flex mb-3';
      typingElement.id = 'typing-indicator';
      typingElement.innerHTML = `
        <div class="typing-dots flex space-x-2 px-4 py-2">
              <span class=""></span>
              <span class=""></span>
              <span class=""></span>
          </div>
      `;
      chatMessages.appendChild(typingElement);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    
      // Simulare răspuns după delay scurt (ex: 500ms)
      setTimeout(() => {
        typingElement.remove();
    
        const replyElement = document.createElement('div');
        replyElement.className = 'flex mb-3';

        replyElement.innerHTML = `
          <div class="bg-gray-200 text-black rounded-lg py-2 px-4 max-w-[70%]">
            ${message}
          </div>
        `;
        chatMessages.appendChild(replyElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      }, 2000);
    }
  
})();