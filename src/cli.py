# src/cli.py
import sys
import os
from colorama import init, Fore, Style

init()

class FollMuzCLI:
    def __init__(self):
        self.downloader = None

    def get_downloader(self):
        if self.downloader is None:
            from src.follmuz_downloader import FollMuzDownloader
            self.downloader = FollMuzDownloader()
        return self.downloader
        
    def print_banner(self):
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║                                                              ║
║         YouTube Music Downloader with MusicBrainz           ║
║              Скачивай музыку с правильными тегами           ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)
    
    def single_mode(self):
        print(f"\n{Fore.CYAN}🎵 Скачивание одного трека{Style.RESET_ALL}")
        
        artist = input(f"{Fore.YELLOW}Исполнитель: {Style.RESET_ALL}").strip()
        title = input(f"{Fore.YELLOW}Название трека: {Style.RESET_ALL}").strip()
        
        if not artist or not title:
            print(f"{Fore.RED}Исполнитель и название трека обязательны{Style.RESET_ALL}")
            return
        
        save_path = input(f"{Fore.YELLOW}Папка для сохранения [Enter - downloads]: {Style.RESET_ALL}").strip()
        if not save_path:
            save_path = 'downloads'
        
        self.get_downloader().search_and_download(artist, title, save_path)
    
    def playlist_mode(self):
        print(f"\n{Fore.CYAN}📋 Скачивание плейлиста{Style.RESET_ALL}")
        print("Формат файла: исполнитель|название|модификация (построчно)")
        print("Пример: Мияги|Тамада|")
        print("Пример: Баста|Сансара|remix")
        
        file_path = input(f"{Fore.YELLOW}Путь к файлу с плейлистом: {Style.RESET_ALL}").strip()
        
        if not os.path.exists(file_path):
            print(f"{Fore.RED}Файл не найден{Style.RESET_ALL}")
            return
        
        save_path = input(f"{Fore.YELLOW}Папка для сохранения [Enter - downloads]: {Style.RESET_ALL}").strip()
        if not save_path:
            save_path = 'downloads'
        
        tracks = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '|' in line:
                        parts = [part.strip() for part in line.split('|')]
                        if len(parts) >= 2:
                            tracks.append({
                                'artist': parts[0],
                                'title': parts[1],
                                'modification': parts[2] if len(parts) >= 3 else ''
                            })
                        else:
                            print(f"{Fore.YELLOW}Строка {line_num} пропущена (недостаточно полей): {line}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}Строка {line_num} пропущена (нет разделителя |): {line}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Ошибка чтения файла: {e}{Style.RESET_ALL}")
            return
        
        if not tracks:
            print(f"{Fore.YELLOW}В файле не найдено треков в правильном формате{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}Найдено треков: {len(tracks)}{Style.RESET_ALL}")
        
        successful = 0
        for i, track in enumerate(tracks, 1):
            print(f"\n{Fore.WHITE}[{i}/{len(tracks)}] {track['artist']} - {track['title']}{Style.RESET_ALL}")
            if self.get_downloader().search_and_download(
                artist=track['artist'],
                title=track['title'],
                save_path=save_path,
                modification=track.get('modification', '')
            ):
                successful += 1
            else:
                print(f"{Fore.RED}✗ Не удалось скачать{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}✅ Скачано {successful} из {len(tracks)} треков{Style.RESET_ALL}")
    
    def run(self):
        self.print_banner()
        
        while True:
            print(f"\n{Fore.CYAN}Главное меню:{Style.RESET_ALL}")
            print("1. 🎵 Скачать один трек")
            print("2. 📋 Скачать плейлист из файла")
            print("3. 🚪 Выход")
            
            choice = input(f"\n{Fore.YELLOW}Выберите действие: {Style.RESET_ALL}").strip()
            
            if choice == '1':
                self.single_mode()
            elif choice == '2':
                self.playlist_mode()
            elif choice == '3':
                print(f"{Fore.GREEN}До свидания!{Style.RESET_ALL}")
                break
            else:
                print(f"{Fore.RED}Неверный выбор{Style.RESET_ALL}")
            
            if choice != '3':
                input(f"\n{Fore.CYAN}Нажмите Enter для продолжения...{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        cli = FollMuzCLI()
        cli.run()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Программа прервана{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
