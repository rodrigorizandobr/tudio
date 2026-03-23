import pytest
from unittest.mock import patch, MagicMock, mock_open
from backend.services.music_service import MusicService, music_service
from backend.models.music import MusicModel
from fastapi import UploadFile
from io import BytesIO

class TestMusicService:
    @pytest.fixture
    def service(self):
        return MusicService()
    
    @pytest.fixture
    def mock_repo(self):
        with patch("backend.services.music_service.music_repository") as mock:
            yield mock
    
    def test_list_all(self, service, mock_repo):
        """Test list_all returns all music"""
        music1 = MusicModel(id=1, title="Song1", artist="Artist1", genre="Rock", mood="Happy", filename="song1.mp3", file_path="musics/song1.mp3", duration_seconds=180)
        music2 = MusicModel(id=2, title="Song2", artist="Artist2", genre="Jazz", mood="Calm", filename="song2.mp3", file_path="musics/song2.mp3", duration_seconds=200)
        mock_repo.list_all.return_value = [music1, music2]
        
        result = service.list_all()
        
        assert len(result) == 2
        assert result[0].title == "Song1"
        assert result[1].title == "Song2"
        mock_repo.list_all.assert_called_once()
    
    def test_get(self, service, mock_repo):
        """Test get returns specific music"""
        music = MusicModel(id=1, title="Song1", artist="Artist1", genre="Rock", mood="Happy", filename="song1.mp3", file_path="musics/song1.mp3", duration_seconds=180)
        mock_repo.get.return_value = music
        
        result = service.get(1)
        
        assert result.id == 1
        assert result.title == "Song1"
        mock_repo.get.assert_called_once_with(1)
    
    @patch("backend.services.music_service.shutil.copyfileobj")
    @patch("backend.services.music_service.MP3")
    @patch("builtins.open", new_callable=mock_open)
    def test_upload_music_success(self, mock_file, mock_mp3, mock_copy, service, mock_repo):
        """Test upload_music successfully uploads and extracts metadata"""
        # Mock upload file
        file_content = b"fake mp3 content"
        upload_file = UploadFile(filename="test.mp3", file=BytesIO(file_content))
        
        # Mock MP3 metadata
        mock_audio = MagicMock()
        mock_audio.info.length = 180.5
        mock_mp3.return_value = mock_audio
        
        # Mock repo save
        saved_music = MusicModel(
            id=1,
            title="Test Song",
            artist="Test Artist",
            genre="Rock",
            mood="Happy",
            filename="test.mp3",
            file_path="musics/test.mp3",
            duration_seconds=180
        )
        mock_repo.save.return_value = saved_music
        
        result = service.upload_music(
            file=upload_file,
            title="Test Song",
            artist="Test Artist",
            genre="Rock",
            mood="Happy"
        )
        
        assert result.id == 1
        assert result.title == "Test Song"
        assert result.duration_seconds == 180
        mock_copy.assert_called_once()
        mock_repo.save.assert_called_once()
    
    @patch("backend.services.music_service.shutil.copyfileobj")
    @patch("backend.services.music_service.MP3")
    @patch("builtins.open", new_callable=mock_open)
    def test_upload_music_duration_extraction_fails(self, mock_file, mock_mp3, mock_copy, service, mock_repo):
        """Test upload_music handles duration extraction failure gracefully"""
        upload_file = UploadFile(filename="bad.mp3", file=BytesIO(b"corrupted"))
        
        # Mock MP3 to raise exception
        mock_mp3.side_effect = Exception("Invalid MP3")
        
        saved_music = MusicModel(
            id=1,
            title="Bad Song",
            artist="Test",
            genre="Rock",
            mood="Sad",
            filename="bad.mp3",
            file_path="musics/bad.mp3",
            duration_seconds=0  # Default when extraction fails
        )
        mock_repo.save.return_value = saved_music
        
        result = service.upload_music(
            file=upload_file,
            title="Bad Song",
            artist="Test",
            genre="Rock",
            mood="Sad"
        )
        
        assert result.duration_seconds == 0
        mock_repo.save.assert_called_once()
    
    def test_delete_music(self, service, mock_repo):
        """Test delete_music deletes successfully"""
        mock_repo.delete.return_value = True
        
        result = service.delete_music(1)
        
        assert result is True
        mock_repo.delete.assert_called_once_with(1)
