import os
import subprocess
import json
from src.logger import Logger

logger = Logger()


class TagEditor:
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
        self.mutagen_available = self._check_mutagen()
        logger.info(
            f"TagEditor инициализирован, FFmpeg: {self.ffmpeg_available}, "
            f"Mutagen: {self.mutagen_available}"
        )

    def _check_ffmpeg(self):
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def _check_mutagen(self):
        try:
            import mutagen  # noqa: F401
            return True
        except ImportError:
            return False

    def _is_mp3(self, filepath: str) -> bool:
        return filepath.lower().endswith(".mp3")

    def add_tags_with_ffmpeg(self, filepath, metadata):
        if not self.ffmpeg_available:
            logger.warning("FFmpeg не доступен, пропускаю добавление тегов")
            return False

        if not os.path.exists(filepath):
            logger.error(f"Файл не найден: {filepath}")
            return False

        try:
            base, ext = os.path.splitext(filepath)
            temp_file = f"{base}.temp{ext}"

            cmd = ['ffmpeg', '-i', filepath, '-c', 'copy', '-map_metadata', '0']

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
                timeout=30,
                check=False,
            )

            if result.returncode == 0 and os.path.exists(temp_file):
                try:
                    os.replace(temp_file, filepath)
                except OSError as e:
                    logger.error(f"Ошибка при замене файла: {e}")
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False

                logger.info(f"Метаданные добавлены через FFmpeg для {os.path.basename(filepath)}")
                return True
            else:
                logger.error(f"Ошибка FFmpeg: {result.stderr}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False

        except Exception as e:
            logger.error(f"Ошибка при добавлении тегов через FFmpeg: {e}")
            if 'temp_file' in locals() and os.path.exists(temp_file):
                os.remove(temp_file)
            return False

    def add_tags_with_mutagen(self, filepath, metadata):
        if not self.mutagen_available:
            logger.warning("Mutagen не установлен, пропускаю добавление тегов")
            return False

        if not self._is_mp3(filepath):
            logger.warning(f"Mutagen-теги поддерживаются только для MP3: {filepath}")
            return False

        if not os.path.exists(filepath):
            logger.error(f"Файл не найден: {filepath}")
            return False

        try:
            import mutagen
            from mutagen.easyid3 import EasyID3
            from mutagen.id3 import ID3

            try:
                audio = EasyID3(filepath)
            except mutagen.id3.ID3NoHeaderError:
                # Создаём новые ID3-теги
                audio = ID3()
                audio.save(filepath)
                audio = EasyID3(filepath)

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
        if not os.path.exists(filepath):
            logger.error(f"Файл не найден: {filepath}")
            return False

        if self.ffmpeg_available and self.add_tags_with_ffmpeg(filepath, metadata):
            return True

        if self.mutagen_available and self.add_tags_with_mutagen(filepath, metadata):
            return True

        logger.warning("Не удалось добавить теги: FFmpeg и Mutagen не сработали")
        return False

    def get_tags(self, filepath):
        if not os.path.exists(filepath):
            logger.error(f"Файл не найден: {filepath}")
            return {}

        try:
            if self.ffmpeg_available:
                result = subprocess.run(
                    [
                        'ffprobe', '-v', 'quiet',
                        '-print_format', 'json',
                        '-show_format',
                        filepath,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )

                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if 'format' in data and 'tags' in data['format']:
                        return data['format']['tags']

        except Exception as e:
            logger.error(f"Ошибка при получении тегов через ffprobe: {e}")

        try:
            if self.mutagen_available:
                import mutagen
                from mutagen.easyid3 import EasyID3

                if self._is_mp3(filepath):
                    try:
                        audio = EasyID3(filepath)
                        tags = {}
                        for key in audio:
                            values = audio[key]
                            if values:
                                tags[key] = values[0]
                        return tags
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Ошибка при получении тегов через mutagen: {e}")

        return {}