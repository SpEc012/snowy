// GSAP Animations for Snowy Market Gen
// Using the latest GSAP which is now free

// Initialize GSAP animations
function initAnimations() {
  // Register plugins
  gsap.registerPlugin(ScrollTrigger);
  
  // Animate navbar on load
  gsap.from('.navbar', {
    y: -50,
    opacity: 0,
    duration: 0.8,
    ease: 'power3.out'
  });
  
  // Animate main content
  gsap.from('.container > *', {
    y: 30,
    opacity: 0,
    stagger: 0.2,
    duration: 0.8,
    ease: 'power2.out',
    delay: 0.3
  });
  
  // Animate features with scroll trigger
  // First ensure all features are visible by default
  gsap.set('.feature', {
    opacity: 1,
    y: 0,
    clearProps: 'all'
  });
  
  // Then apply the animation
  gsap.from('.feature', {
    scrollTrigger: {
      trigger: '.features',
      start: 'top 80%',
    },
    y: 50,
    opacity: 0,
    stagger: 0.2,
    duration: 0.8,
    ease: 'back.out(1.2)',
    onComplete: function() {
      // Ensure features remain visible after animation
      gsap.set('.feature', {clearProps: 'all'});
    }
  });
}

// Modal animations
function animateModalOpen() {
  const modal = document.getElementById('generatorModal');
  if (!modal) return;
  
  gsap.set(modal, { display: 'flex' });
  
  gsap.fromTo('.modal-content', 
    { 
      y: 30, 
      opacity: 0, 
      scale: 0.9 
    }, 
    { 
      y: 0, 
      opacity: 1, 
      scale: 1, 
      duration: 0.5, 
      ease: 'back.out(1.7)' 
    }
  );
  
  gsap.fromTo(modal, 
    { backgroundColor: 'rgba(0, 0, 0, 0)' }, 
    { backgroundColor: 'rgba(0, 0, 0, 0.8)', duration: 0.5 }
  );
}

function animateModalClose() {
  const modal = document.getElementById('generatorModal');
  if (!modal) return;
  
  const tl = gsap.timeline({
    onComplete: () => {
      gsap.set(modal, { display: 'none' });
    }
  });
  
  tl.to('.modal-content', { 
    y: 20, 
    opacity: 0, 
    scale: 0.9, 
    duration: 0.3, 
    ease: 'power2.in' 
  });
  
  tl.to(modal, { 
    backgroundColor: 'rgba(0, 0, 0, 0)', 
    duration: 0.3 
  }, "-=0.2");
}

// Account generation animation
function animateAccountGeneration() {
  const tl = gsap.timeline();
  
  // Hide account info and show loader
  tl.set('.account-info', { display: 'none' });
  tl.set('.loader', { display: 'block', opacity: 0 });
  
  // Animate the loader appearing
  tl.to('.loader', {
    opacity: 1,
    duration: 0.3,
    ease: 'power2.out'
  });
  
  // Handle loading animation
  const typingTextTl = gsap.timeline({repeat: -1, repeatDelay: 0.3});
  typingTextTl.to('.loader-text', {duration: 0.5, text: 'Loading.', ease: 'none'})
    .to('.loader-text', {duration: 0.5, text: 'Loading..', ease: 'none'})
    .to('.loader-text', {duration: 0.5, text: 'Loading...', ease: 'none'});
    
  // Add a subtle pulse animation to the loader only if it exists
  const loaderElement = document.querySelector('.loader');
  if (loaderElement) {
    gsap.to(loaderElement, {
      scale: 1.05,
      opacity: 0.9,
      duration: 0.8,
      repeat: -1,
      yoyo: true,
      ease: 'power1.inOut'
    });
  }
  
  // Add typing animation to the loader text
  const loaderText = document.querySelector('.loader-text');
  if (loaderText) {
    const originalText = loaderText.textContent;
    const textArray = ['Generating account', 'Generating account.', 'Generating account..', 'Generating account...'];
    let currentIndex = 0;
    
    // Create a typing animation
    const typingInterval = setInterval(() => {
      loaderText.textContent = textArray[currentIndex];
      currentIndex = (currentIndex + 1) % textArray.length;
    }, 300);
    
    // Store the interval ID to clear it later
    window.loaderTypingInterval = typingInterval;
  }
  
  return tl;
}

function animateAccountDisplay() {
  const tl = gsap.timeline();
  
  // Clear the typing interval if it exists
  if (window.loaderTypingInterval) {
    clearInterval(window.loaderTypingInterval);
    window.loaderTypingInterval = null;
  }
  
  // Hide loader with a fade out
  tl.to('.loader', {
    opacity: 0,
    duration: 0.3,
    ease: 'power2.in',
    onComplete: () => {
      document.querySelector('.loader').style.display = 'none';
      document.querySelector('.account-info').style.display = 'block';
    }
  });
  
  // Create a staggered reveal animation for account info
  tl.fromTo('.service-icon-large', {
    scale: 0.5,
    opacity: 0,
    y: -20
  }, {
    scale: 1,
    opacity: 1,
    y: 0,
    duration: 0.6,
    ease: 'elastic.out(1, 0.5)'
  });
  
  // Animate the account details with a typing effect
  tl.fromTo('.account-details', { 
    y: 15, 
    opacity: 0,
    scale: 0.95
  }, {
    y: 0,
    opacity: 1,
    scale: 1, 
    duration: 0.5, 
    ease: 'back.out(1.7)',
    onComplete: () => {
      // Add a subtle highlight effect to the input
      gsap.fromTo('#accountDetails', 
        { boxShadow: '0 0 0 2px rgba(155, 77, 255, 0.7)' },
        { boxShadow: '0 0 0 0px rgba(155, 77, 255, 0)', duration: 1.5, ease: 'power2.out' }
      );
    }
  }, '-=0.3');
  
  // Animate the copy button with a bounce
  tl.fromTo('.copy-btn', {
    scale: 0,
    rotation: -45
  }, {
    scale: 1,
    rotation: 0,
    duration: 0.5,
    ease: 'back.out(2)'
  }, '-=0.4');
  
  // Animate the account actions
  tl.fromTo('.account-actions', {
    y: 15,
    opacity: 0
  }, {
    y: 0,
    opacity: 1,
    duration: 0.4,
    ease: 'power2.out'
  }, '-=0.3');
  
  return tl;
}

// Copy button animation
function animateCopyButton(button) {
  gsap.to(button, {
    scale: 1.2,
    duration: 0.2,
    ease: 'power2.out',
    onComplete: () => {
      gsap.to(button, {
        scale: 1,
        duration: 0.2,
        ease: 'power2.in'
      });
    }
  });
}

// History item animations
function animateHistoryItems() {
  gsap.from('.history-item', {
    opacity: 0,
    y: 20,
    stagger: 0.1,
    duration: 0.5,
    ease: 'power2.out'
  });
}

// Login/Register form animations
function animateAuthForm() {
  gsap.from('.auth-box', {
    y: 30,
    opacity: 0,
    duration: 0.8,
    ease: 'back.out(1.7)'
  });
  
  gsap.from('.input-group', {
    x: -20,
    opacity: 0,
    stagger: 0.2,
    duration: 0.6,
    delay: 0.3,
    ease: 'power2.out'
  });
}

// Notification animation
function showNotification(message, type = 'success') {
  // BLOCK ALL COOLDOWN WARNING MESSAGES
  if (message.includes('wait') && message.includes('seconds') && message.includes('generating again')) {
    console.log('Blocking cooldown notification:', message);
    return; // Don't show cooldown warnings at all
  }
  
  // Create notification element if it doesn't exist
  let notification = document.querySelector('.notification');
  if (!notification) {
    notification = document.createElement('div');
    notification.className = 'notification';
    document.body.appendChild(notification);
  }
  
  // Set content and type
  notification.innerHTML = `
    <div class="notification-icon">
      <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
    </div>
    <div class="notification-message">${message}</div>
  `;
  notification.className = `notification ${type}`;
  
  // Clear any existing animations
  gsap.killTweensOf(notification);
  
  // Animate notification
  gsap.fromTo(notification,
    { y: -100, opacity: 0 },
    { 
      y: 0, 
      opacity: 1, 
      duration: 0.5, 
      ease: 'power3.out',
      onComplete: () => {
        // Auto hide after 5 seconds (increased from 3)
        gsap.to(notification, {
          y: -100,
          opacity: 0,
          delay: 5,
          duration: 0.5,
          ease: 'power3.in'
        });
      }
    }
  );
}

// Export all animations
window.RavenAnimations = {
  init: initAnimations,
  modal: {
    open: animateModalOpen,
    close: animateModalClose
  },
  account: {
    generating: animateAccountGeneration,
    display: animateAccountDisplay
  },
  copyButton: animateCopyButton,
  historyItems: animateHistoryItems,
  authForm: animateAuthForm,
  notification: showNotification
}

// Export all animations with new branding
window.SnowyAnimations = {
  init: initAnimations,
  modal: {
    open: animateModalOpen,
    close: animateModalClose
  },
  account: {
    generating: animateAccountGeneration,
    display: animateAccountDisplay
  },
  copyButton: animateCopyButton,
  historyItems: animateHistoryItems,
  authForm: animateAuthForm,
  notification: showNotification
};
