/**
 * Internationalization (i18n) Module
 * Supports Chinese and English switching
 */

const I18N = {
    currentLang: localStorage.getItem('opc_language') || 'zh',
    translations: {},
    
    async init() {
        await this.loadTranslations(this.currentLang);
        this.applyTranslations();
        this.updateLanguageButton();
        
        // Update HTML lang attribute
        document.documentElement.lang = this.currentLang === 'zh' ? 'zh-CN' : 'en';
    },
    
    async loadTranslations(lang) {
        try {
            // Use absolute path to ensure correct loading
            const baseUrl = window.location.pathname.includes('/dashboard') 
                ? '/dashboard/' 
                : '/';
            const response = await fetch(`${baseUrl}locales/${lang}.json`);
            if (response.ok) {
                this.translations = await response.json();
                console.log(`[i18n] Loaded ${lang} translations`);
            } else {
                console.error(`[i18n] Failed to load ${lang}: ${response.status}`);
            }
        } catch (error) {
            console.error('[i18n] Failed to load translations:', error);
        }
    },
    
    t(key) {
        const keys = key.split('.');
        let value = this.translations;
        
        for (const k of keys) {
            if (value && typeof value === 'object' && k in value) {
                value = value[k];
            } else {
                return null; // Return null if translation not found
            }
        }
        
        return value || null;
    },
    
    async switchLanguage(lang) {
        if (lang === this.currentLang) return;
        
        this.currentLang = lang;
        localStorage.setItem('opc_language', lang);
        
        await this.loadTranslations(lang);
        this.applyTranslations();
        this.updateLanguageButton();
        
        // Update HTML lang attribute
        document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
        
        // Show feedback
        const feedback = lang === 'zh' ? '已切换到中文' : 'Switched to English';
        console.log(`[i18n] ${feedback}`);
        
        // Refresh dynamic content
        if (typeof loadPartnerState === 'function') {
            loadPartnerState();
        }
    },
    
    applyTranslations() {
        // Apply to elements with data-i18n attribute
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = this.t(key);
            
            if (translation) {
                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                    el.placeholder = translation;
                } else {
                    el.textContent = translation;
                }
            }
        });
        
        // Update document title
        const titleTranslation = this.t('app.title');
        if (titleTranslation) {
            document.title = titleTranslation;
        }
    },
    
    updateLanguageButton() {
        // Update select element
        const select = document.getElementById('lang-select');
        if (select) {
            select.value = this.currentLang;
        }
    },
    
    toggle() {
        // Deprecated: use switchLanguage instead
        const newLang = this.currentLang === 'zh' ? 'en' : 'zh';
        this.switchLanguage(newLang);
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    I18N.init();
});
