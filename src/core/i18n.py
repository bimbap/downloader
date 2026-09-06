# =============================================================================
# downloader/src/core/i18n.py – Internationalization & Localization (ID / EN)
# =============================================================================
from core.config import load_config, save_config

TRANSLATIONS = {
    "en": {
        # General / Common
        "app_title": "UNIVERSAL MEDIA DOWNLOADER 🚀",
        "back": "Return to Main Menu",
        "back_simple": "Back",
        "cancel": "Cancel",
        "confirm": "Confirm",
        "success": "SUCCESS",
        "failed": "FAILED",
        "error": "ERROR",
        "yes": "YES",
        "no": "NO",
        "storage": "Storage",
        "library": "Library",
        "items": "items",
        "files": "files",
        "empty": "empty",
        "size": "Size",
        "folder": "Folder",
        "author": "Author",
        "caption": "Caption",
        "title": "Title",
        "media_type": "Media Type",
        "destination": "Destination",
        "source_url": "Source URL",
        "fetching_meta": "🔍 Fetching media details...",
        "open_folder": "Open in Explorer 📂",
        "delete_file": "Delete File 🗑",
        "delete_all": "Delete All Files 🗑",
        "play_media": "Play / View Media ▶",
        "file_action": "File Action",
        "all_media": "All Downloads",
        "thanks": "Thank you for using Downloader. See you! 👋",

        # Main Menu
        "menu_smart": "⚡ Smart Download (Paste Any Social Link)",
        "menu_youtube": "🔴 YouTube Downloader (Video, Audio, Playlist)",
        "menu_twitter": "🐦 X / Twitter Downloader (Video, GIF, Photos)",
        "menu_instagram": "📷 Instagram Downloader (Reels, Videos, Photos)",
        "menu_threads": "🧵 Threads Downloader (Video, Photos)",
        "menu_manager": "📁 Manage Downloaded Media",
        "menu_settings": "⚙ Settings & Preferences",
        "menu_exit": "Exit Downloader",

        # Smart & Social Download
        "smart_title": "⚡ Universal Smart Downloader",
        "smart_paste": "Right-click or Ctrl+V to paste your link below:",
        "paste_link": "Paste your link below:",
        "ready_to_download": "Ready to Download",
        "download_media": "Download Media 🚀",
        "download_all_slides": "Download All Slides ({count} files) 🚀",
        "select_specific_slides": "Select Specific Slides 🎯",
        "slide_selection_prompt": "Select Slides to Download:",
        "slide_selection_hint": "Examples: '1,3' for slides 1 & 3, '1-2' for slides 1 & 2, or 'all'",
        "slide_numbers": "Slide numbers [1-{total}]: ",
        "downloading_slides": "Downloading {count} selected slide(s)...",
        "downloading_all_slides": "Downloading all {count} slides...",
        "downloading_media": "Downloading media...",
        "download_success": "Media downloaded & saved successfully!",
        "download_failed": "Could not download media. Please check URL and internet connection.",
        "return_hint": "[Enter] Return  |  [o] Open Folder  |  [p] Play/View Media",
        "invalid_url": "Unsupported or invalid link format.",
        "invalid_url_hint": "Please provide a valid link from YouTube, X, Instagram, or Threads.",

        # Manager View
        "manager_title": "📁 Manage Downloads – Select Platform",
        "manager_select_format": "{icon} {name} – Select Format",
        "all_platforms": "📂 All Platforms [{count} files • {size:.1f} MB]",
        "all_platform_media": "📂 All {name} Media [{count} files • {size:.1f} MB]",
        "open_root_folder": "[Open Downloads Folder in Explorer 📂]",
        "open_platform_folder": "[Open {name} Folder in Explorer 📂]",
        "open_this_folder": "[Open This Folder in Explorer 📂]",
        "delete_all_in_folder": "[Delete All Files in This Folder 🗑]",
        "no_files_found": "No downloaded media files found.",
        "no_files_category": "No files remaining in this folder.",
        "confirm_delete_title": "⚠ CONFIRM FOLDER DELETION",
        "confirm_delete_msg": "Are you sure you want to delete ALL {count} files in:",
        "confirm_delete_prompt": "Type 'YES' to confirm, or press Enter to cancel:",
        "deleted_success": "✔ Deleted {count} file(s) successfully.",

        # Settings
        "settings_title": "SETTINGS & PREFERENCES ⚙",
        "setting_video": "Video Settings 🎬",
        "setting_audio": "Audio Settings 🎵",
        "setting_style": "Filename Style 🏷",
        "setting_storage": "Storage & Folders 📁",
        "setting_language": "Language / Bahasa 🌐",
        "setting_cookies": "Browser Cookies (Bypass Login) 🍪",
        "setting_clean": "Clean Cache & Temp Files 🧹",
        "setting_reset": "Reset to Default Settings 🔄",

        # Settings Detail
        "lang_select_title": "Select Display Language 🌐",
        "cookies_select_title": "Select Browser for Cookies 🍪",
        "cookies_desc": "Imports session cookies from your local browser to download 18+ YouTube videos and restricted Instagram/X posts.",
        "cache_cleaned": "✔ Cleaned {count} temporary file(s), freed {size:.2f} MB of disk space.",
        "cache_already_clean": "✔ Cache is already clean. No temporary files found.",
        "reset_confirm_title": "⚠ CONFIRM CONFIGURATION RESET",
        "reset_confirm_msg": "Are you sure you want to reset all settings to factory defaults?",
        "reset_success": "✔ All settings have been reset to factory defaults.",
    },

    "id": {
        # General / Common
        "app_title": "DOWNLOADER MEDIA UNIVERSAL 🚀",
        "back": "Kembali ke Menu Utama",
        "back_simple": "Kembali",
        "cancel": "Batalkan",
        "confirm": "Konfirmasi",
        "success": "BERHASIL",
        "failed": "GAGAL",
        "error": "ERROR",
        "yes": "YA",
        "no": "TIDAK",
        "storage": "Penyimpanan",
        "library": "Pustaka",
        "items": "item",
        "files": "file",
        "empty": "kosong",
        "size": "Ukuran",
        "folder": "Folder",
        "author": "Pembuat / Akun",
        "caption": "Keterangan",
        "title": "Judul",
        "media_type": "Tipe Media",
        "destination": "Lokasi Simpan",
        "source_url": "URL Sumber",
        "fetching_meta": "🔍 Mengambil informasi media...",
        "open_folder": "Buka di Explorer 📂",
        "delete_file": "Hapus File 🗑",
        "delete_all": "Hapus Semua File 🗑",
        "play_media": "Putar / Lihat Media ▶",
        "file_action": "Aksi File",
        "all_media": "Semua Unduhan",
        "thanks": "Terima kasih telah menggunakan Downloader. Sampai jumpa! 👋",

        # Main Menu
        "menu_smart": "⚡ Unduh Cerdas (Tempel Link Medsos Apa Saja)",
        "menu_youtube": "🔴 YouTube Downloader (Video, Audio, Playlist)",
        "menu_twitter": "🐦 X / Twitter Downloader (Video, GIF, Foto)",
        "menu_instagram": "📷 Instagram Downloader (Reels, Video, Foto)",
        "menu_threads": "🧵 Threads Downloader (Video, Foto)",
        "menu_manager": "📁 Kelola Media yang Diunduh",
        "menu_settings": "⚙ Pengaturan & Preferensi",
        "menu_exit": "Keluar dari Aplikasi",

        # Smart & Social Download
        "smart_title": "⚡ Downloader Universal Cerdas",
        "smart_paste": "Klik kanan atau Ctrl+V untuk menempelkan tautan:",
        "paste_link": "Tempelkan tautan di bawah ini:",
        "ready_to_download": "Siap Mengunduh",
        "download_media": "Unduh Media 🚀",
        "download_all_slides": "Unduh Semua Slide ({count} file) 🚀",
        "select_specific_slides": "Pilih Slide Tertentu 🎯",
        "slide_selection_prompt": "Pilih Nomor Slide untuk Diunduh:",
        "slide_selection_hint": "Contoh: '1,3' untuk slide 1 & 3, '1-2' untuk slide 1 & 2, atau 'all'",
        "slide_numbers": "Nomor slide [1-{total}]: ",
        "downloading_slides": "Mengunduh {count} slide yang dipilih...",
        "downloading_all_slides": "Mengunduh semua {count} slide...",
        "downloading_media": "Mengunduh file media...",
        "download_success": "Media berhasil diunduh dan disimpan!",
        "download_failed": "Gagal mengunduh media. Periksa URL dan koneksi internet Anda.",
        "return_hint": "[Enter] Kembali  |  [o] Buka Folder  |  [p] Putar/Buka Media",
        "invalid_url": "Format tautan tidak didukung atau tidak valid.",
        "invalid_url_hint": "Pastikan menggunakan link valid dari YouTube, X, Instagram, atau Threads.",

        # Manager View
        "manager_title": "📁 Kelola Unduhan – Pilih Platform",
        "manager_select_format": "{icon} {name} – Pilih Format",
        "all_platforms": "📂 Semua Platform [{count} file • {size:.1f} MB]",
        "all_platform_media": "📂 Semua Media {name} [{count} file • {size:.1f} MB]",
        "open_root_folder": "[Buka Folder Utama Unduhan di Explorer 📂]",
        "open_platform_folder": "[Buka Folder {name} di Explorer 📂]",
        "open_this_folder": "[Buka Folder Ini di Explorer 📂]",
        "delete_all_in_folder": "[Hapus Semua File di Folder Ini 🗑]",
        "no_files_found": "Tidak ada file unduhan yang ditemukan.",
        "no_files_category": "Tidak ada file yang tersisa di folder ini.",
        "confirm_delete_title": "⚠ KONFIRMASI PENGHAPUSAN FOLDER",
        "confirm_delete_msg": "Apakah Anda yakin ingin menghapus SEMUA {count} file di:",
        "confirm_delete_prompt": "Ketik 'YA' untuk konfirmasi, atau tekan Enter untuk batal:",
        "deleted_success": "✔ Berhasil menghapus {count} file.",

        # Settings
        "settings_title": "PENGATURAN & PREFERENSI ⚙",
        "setting_video": "Pengaturan Video 🎬",
        "setting_audio": "Pengaturan Audio 🎵",
        "setting_style": "Format Nama File 🏷",
        "setting_storage": "Penyimpanan & Folder 📁",
        "setting_language": "Bahasa / Language 🌐",
        "setting_cookies": "Cookies Browser (Bypass Login) 🍪",
        "setting_clean": "Bersihkan Cache & File Sementara 🧹",
        "setting_reset": "Kembalikan ke Pengaturan Awal 🔄",

        # Settings Detail
        "lang_select_title": "Pilih Bahasa Tampilan 🌐",
        "cookies_select_title": "Pilih Browser untuk Cookies 🍪",
        "cookies_desc": "Membaca cookies session dari browser lokal Anda untuk bypass video 18+ YouTube & post Instagram/X yang butuh login.",
        "cache_cleaned": "✔ Berhasil membersihkan {count} file sementara, menghemat {size:.2f} MB ruang disk.",
        "cache_already_clean": "✔ Cache sudah bersih. Tidak ada file sementara yang ditemukan.",
        "reset_confirm_title": "⚠ KONFIRMASI RESET PENGATURAN",
        "reset_confirm_msg": "Apakah Anda yakin ingin mengembalikan semua pengaturan ke bawaan awal?",
        "reset_success": "✔ Semua pengaturan telah berhasil dikembalikan ke bawaan pabrik.",
    }
}


def get_current_language() -> str:
    """Returns the currently active language code ('id' or 'en')."""
    cfg = load_config()
    lang = cfg.get("language", "id").lower()
    return "en" if lang.startswith("en") else "id"


def set_current_language(lang_code: str) -> bool:
    """Updates the active language in config."""
    code = "en" if lang_code.lower().startswith("en") else "id"
    cfg = load_config()
    cfg["language"] = code
    save_config(cfg)
    return True


def t(key: str, **kwargs) -> str:
    """Translates a key into the active language with optional kwargs formatting."""
    lang = get_current_language()
    dict_lang = TRANSLATIONS.get(lang, TRANSLATIONS["id"])
    
    # Fallback to id if key not found in active language
    template = dict_lang.get(key) or TRANSLATIONS["id"].get(key) or key
    
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
