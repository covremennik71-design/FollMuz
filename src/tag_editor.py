import os
import subprocess
import json
from src.logger import Logger

logger = Logger()

class TagEditor:
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
        logger.info(f"TagEditor инициализирован, FFmpeg доступен: {self.ffmpeg_available}")

    def _check_ffmpeg(self):
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def _check_mutagen(self):
        try:
            import mutagen
            return True
        except ImportError:
            return False

    def add_tags_with_ffmpeg(self, filepath, metadata):
        if not self.ffmpeg_available:
            logger.warning("FFmpeg не доступен, пропускаю добавление тегов")
            return False

        try:
            temp_file = filepath + ".temp.mp3"
            
            cmd = ['ffmpeg', '-i', filepath, '-c', 'copy']
            
            if 'title' in metadata:
                cmd.extend(['-metadata', f'title={metadata["title"]}'])
            if 'artist' in metadata:
                cmd.extend(['-metadata', f'artist={metadata["artist"]}'])
            if 'album' in metadata:
                cmd.extend(['-metadata', f'album={metadata["album"]}'])
            if 'date' in metadata:
                cmd.extend(['-metadata', f'date={metadata["date"]}'])
            if 'genre' in metadata:
                cmd.extend(['-metadata', f'genre={metadata["genre"]}'])
            if 'track' in metadata:
                cmd.extend(['-metadata', f'track={metadata["track"]}'])
            
            cmd.extend(['-y', temp_file])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(temp_file):
                os.remove(filepath)
                os.rename(temp_file, filepath)
                logger.info(f"Метаданные добавлены через FFmpeg для {os.path.basename(filepath)}")
                return True
            else:
                logger.error(f"Ошибка FFmpeg: {result.stderr}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении тегов через FFmpeg: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False

    def add_tags_with_mutagen(self, filepath, metadata):
        try:
            import mutagen
            from mutagen.easyid3 import EasyID3
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TRCK
            
            try:
                audio = EasyID3(filepath)
            except mutagen.id3.ID3NoHeaderError:
                audio = mutagen.File(filepath, easy=True)
                audio.add_tags()
            
            if 'title' in metadata:
                audio['title'] = metadata['title']
            if 'artist' in metadata:
                audio['artist'] = metadata['artist']
            if 'album' in metadata:
                audio['album'] = metadata['album']
            if 'date' in metadata:
                audio['date'] = metadata['date']
            if 'genre' in metadata:
                audio['genre'] = metadata['genre']
            if 'track' in metadata:
                audio['tracknumber'] = str(metadata['track'])
            
            audio.save()
            logger.info(f"Метаданные добавлены через mutagen для {os.path.basename(filepath)}")
            return True
            
        except ImportError:
            logger.warning("Mutagen не установлен, пропускаю добавление тегов")
            return False
        except Exception as e:
            logger.error(f"Ошибка при добавлении тегов через mutagen: {e}")
            return False

    def add_tags(self, filepath, metadata):
        if self.add_tags_with_ffmpeg(filepath, metadata):
            return True
        
        return self.add_tags_with_mutagen(filepath, metadata)

    def get_tags(self, filepath):
        try:
            if self.ffmpeg_available:
                result = subprocess.run(
                    ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if 'format' in data and 'tags' in data['format']:
                        return data['format']['tags']
            
            if self._check_mutagen():
                import mutagen
                from mutagen.easyid3 import EasyID3
                
                try:
                    audio = EasyID3(filepath)
                    tags = {}
                    for key in audio:
                        tags[key] = audio[key][0]
                    return tags
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Ошибка при получении тегов: {e}")
        
        return {}
