"""XTC format - Comic container format for multiple pages."""

import io
import struct
import time
from typing import Optional
from dataclasses import dataclass


@dataclass
class XTCMetadata:
    """Metadata for XTC file."""
    title: str = ""
    author: str = ""
    publisher: str = ""
    language: str = "en-US"
    create_time: int = 0
    cover_page: int = 0xFFFF  # 0xFFFF means no cover
    chapter_count: int = 0


@dataclass
class XTCChapter:
    """Chapter information."""
    name: str
    start_page: int  # 0-based
    end_page: int    # 0-based, inclusive


class XTCWriter:
    """Writer for XTC format files (comic container with XTH pages)."""

    MAGIC = 0x00435458  # "XTC\0" in little-endian
    VERSION = 0x0100     # Version 1.0
    HEADER_SIZE = 48
    METADATA_SIZE = 256
    CHAPTER_SIZE = 96
    INDEX_ENTRY_SIZE = 16

    # Reading direction constants
    DIR_LEFT_TO_RIGHT = 0
    DIR_RIGHT_TO_LEFT = 1
    DIR_TOP_TO_BOTTOM = 2

    def __init__(
        self,
        width: int = 480,
        height: int = 800,
        reading_direction: int = DIR_LEFT_TO_RIGHT,
        metadata: Optional[XTCMetadata] = None,
        chapters: Optional[list[XTCChapter]] = None,
        page_format: str = 'xth'
    ):
        """Initialize XTC writer.

        Args:
            width: Page width in pixels
            height: Page height in pixels
            reading_direction: Reading direction (0=L→R, 1=R→L, 2=Top→Bottom)
            metadata: Optional metadata
            chapters: Optional chapter list
            page_format: Format for pages ('xtg' or 'xth', default: 'xth')
        """
        self.width = width
        self.height = height
        self.reading_direction = reading_direction
        self.metadata = metadata or XTCMetadata(create_time=int(time.time()))
        self.chapters = chapters or []
        self.page_format = page_format.lower()

        if self.page_format not in ('xtg', 'xth'):
            raise ValueError("page_format must be 'xtg' or 'xth'")

        if self.chapters:
            self.metadata.chapter_count = len(self.chapters)

    def _write_header(
        self,
        f: io.BufferedWriter,
        page_count: int,
        metadata_offset: int,
        index_offset: int,
        data_offset: int
    ) -> None:
        """Write XTC header.

        Args:
            f: File object
            page_count: Number of pages
            metadata_offset: Offset to metadata section
            index_offset: Offset to index table
            data_offset: Offset to data area
        """
        has_chapters = len(self.chapters) > 0
        # Metadata section must be written if we have title/author OR chapters
        # (chapter_count is stored in metadata section)
        has_metadata = bool(self.metadata.title or self.metadata.author or has_chapters)

        f.write(struct.pack('<I', self.MAGIC))              # mark (4 bytes)
        f.write(struct.pack('<H', self.VERSION))            # version (2 bytes)
        f.write(struct.pack('<H', page_count))              # pageCount (2 bytes)
        f.write(struct.pack('<B', self.reading_direction))  # readDirection (1 byte)
        f.write(struct.pack('<B', 1 if has_metadata else 0))  # hasMetadata (1 byte)
        f.write(struct.pack('<B', 0))                       # hasThumbnails (1 byte)
        f.write(struct.pack('<B', 1 if has_chapters else 0))  # hasChapters (1 byte)
        f.write(struct.pack('<I', 0))                       # currentPage (4 bytes)
        f.write(struct.pack('<Q', metadata_offset if has_metadata else 0))  # metadataOffset (8)
        f.write(struct.pack('<Q', index_offset))            # indexOffset (8 bytes)
        f.write(struct.pack('<Q', data_offset))             # dataOffset (8 bytes)
        f.write(struct.pack('<Q', 0))                       # thumbOffset (8 bytes)

    def _write_metadata(self, f: io.BufferedWriter) -> None:
        """Write metadata section.

        Args:
            f: File object
        """
        # Title (128 bytes)
        title_bytes = self.metadata.title.encode('utf-8')[:127]
        f.write(title_bytes + b'\x00' * (128 - len(title_bytes)))

        # Author (64 bytes)
        author_bytes = self.metadata.author.encode('utf-8')[:63]
        f.write(author_bytes + b'\x00' * (64 - len(author_bytes)))

        # Publisher (32 bytes)
        publisher_bytes = self.metadata.publisher.encode('utf-8')[:31]
        f.write(publisher_bytes + b'\x00' * (32 - len(publisher_bytes)))

        # Language (16 bytes)
        lang_bytes = self.metadata.language.encode('utf-8')[:15]
        f.write(lang_bytes + b'\x00' * (16 - len(lang_bytes)))

        # Create time (4 bytes)
        f.write(struct.pack('<I', self.metadata.create_time))

        # Cover page (2 bytes)
        f.write(struct.pack('<H', self.metadata.cover_page))

        # Chapter count (2 bytes)
        f.write(struct.pack('<H', len(self.chapters)))

        # Reserved (8 bytes)
        f.write(b'\x00' * 8)

    def _write_chapters(self, f: io.BufferedWriter) -> None:
        """Write chapter section.

        Args:
            f: File object
        """
        for chapter in self.chapters:
            # Chapter name (80 bytes)
            name_bytes = chapter.name.encode('utf-8')[:79]
            f.write(name_bytes + b'\x00' * (80 - len(name_bytes)))

            # Start page (2 bytes)
            f.write(struct.pack('<H', chapter.start_page))

            # End page (2 bytes)
            f.write(struct.pack('<H', chapter.end_page))

            # Reserved (12 bytes)
            f.write(b'\x00' * 12)

    def write(
        self,
        output_path: str,
        frame_data_list: list[bytes]
    ) -> None:
        """Write pre-encoded frame data to XTC file.

        This method accepts pre-encoded XTH or XTG frame data and packages it
        into an XTC container. No image processing is performed.

        Args:
            output_path: Output file path
            frame_data_list: list of pre-encoded XTH/XTG frame data (complete with headers)
        """
        if not frame_data_list:
            raise ValueError("No frames provided")

        page_count = len(frame_data_list)

        # Calculate offsets
        has_chapters = len(self.chapters) > 0
        # Metadata section must be written if we have title/author OR chapters
        # (chapter_count is stored in metadata section)
        has_metadata = bool(self.metadata.title or self.metadata.author or has_chapters)

        current_offset = self.HEADER_SIZE
        metadata_offset = current_offset if has_metadata else 0

        if has_metadata:
            current_offset += self.METADATA_SIZE

        if has_chapters:
            current_offset += self.CHAPTER_SIZE * len(self.chapters)

        index_offset = current_offset
        data_offset = index_offset + (self.INDEX_ENTRY_SIZE * page_count)

        # Write XTC file
        with open(output_path, 'wb') as f:
            # Write header
            self._write_header(f, page_count, metadata_offset, index_offset, data_offset)

            # Write metadata if present
            if has_metadata:
                self._write_metadata(f)

            # Write chapters if present
            if has_chapters:
                self._write_chapters(f)

            # Write index table
            current_data_offset = data_offset
            for frame_data in frame_data_list:
                page_size = len(frame_data)
                f.write(struct.pack('<Q', current_data_offset))  # offset (8 bytes)
                f.write(struct.pack('<I', page_size))            # size (4 bytes)
                f.write(struct.pack('<H', self.width))           # width (2 bytes)
                f.write(struct.pack('<H', self.height))          # height (2 bytes)
                current_data_offset += page_size

            # Write page data
            for frame_data in frame_data_list:
                f.write(frame_data)


class XTCReader:
    """Reader for XTC format files (comic container)."""

    MAGIC = 0x00435458  # "XTC\0" in little-endian
    HEADER_SIZE = 48
    METADATA_SIZE = 256
    CHAPTER_SIZE = 96
    INDEX_ENTRY_SIZE = 16

    def __init__(self):
        """Initialize XTC reader."""
        self.metadata: Optional[XTCMetadata] = None
        self.chapters: list[XTCChapter] = []
        self.width: int = 0
        self.height: int = 0
        self.page_count: int = 0
        self.reading_direction: int = 0

    def read(self, file_path: str) -> list[bytes]:
        """Read XTC file and return list of frame data.

        Args:
            file_path: Path to XTC file

        Returns:
            List of frame data (bytes) for each page
        """
        with open(file_path, 'rb') as f:
            data = f.read()
        return self.decode(data)

    def decode(self, data: bytes) -> list[bytes]:
        """Decode XTC format bytes and return list of frame data.

        Args:
            data: Complete XTC file data

        Returns:
            List of frame data (bytes) for each page
        """
        # Parse header
        magic = struct.unpack('<I', data[0:4])[0]
        if magic != self.MAGIC:
            raise ValueError(f"Invalid XTC magic: {magic:#x}, expected {self.MAGIC:#x}")

        version = struct.unpack('<H', data[4:6])[0]
        self.page_count = struct.unpack('<H', data[6:8])[0]
        self.reading_direction = struct.unpack('<B', data[8:9])[0]
        has_metadata = struct.unpack('<B', data[9:10])[0]
        has_thumbnails = struct.unpack('<B', data[10:11])[0]
        has_chapters = struct.unpack('<B', data[11:12])[0]
        current_page = struct.unpack('<I', data[12:16])[0]
        metadata_offset = struct.unpack('<Q', data[16:24])[0]
        index_offset = struct.unpack('<Q', data[24:32])[0]
        data_offset = struct.unpack('<Q', data[32:40])[0]
        thumb_offset = struct.unpack('<Q', data[40:48])[0]

        # Read metadata if present
        if has_metadata and metadata_offset > 0:
            self._read_metadata(data, metadata_offset)

        # Read chapters if present
        if has_chapters:
            chapter_offset = metadata_offset + self.METADATA_SIZE if has_metadata else self.HEADER_SIZE
            self._read_chapters(data, chapter_offset, has_chapters)

        # Read index table and extract frames
        frames = []
        for i in range(self.page_count):
            entry_offset = index_offset + (i * self.INDEX_ENTRY_SIZE)
            page_offset = struct.unpack('<Q', data[entry_offset:entry_offset+8])[0]
            page_size = struct.unpack('<I', data[entry_offset+8:entry_offset+12])[0]
            page_width = struct.unpack('<H', data[entry_offset+12:entry_offset+14])[0]
            page_height = struct.unpack('<H', data[entry_offset+14:entry_offset+16])[0]

            # Store dimensions from first page
            if i == 0:
                self.width = page_width
                self.height = page_height

            # Extract frame data
            frame_data = data[page_offset:page_offset+page_size]
            frames.append(frame_data)

        return frames

    def _read_metadata(self, data: bytes, offset: int) -> None:
        """Parse metadata section.

        Args:
            data: Complete file data
            offset: Offset to metadata section
        """
        # Title (128 bytes)
        title_bytes = data[offset:offset+128]
        title = title_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')

        # Author (64 bytes)
        author_bytes = data[offset+128:offset+192]
        author = author_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')

        # Publisher (32 bytes)
        publisher_bytes = data[offset+192:offset+224]
        publisher = publisher_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')

        # Language (16 bytes)
        lang_bytes = data[offset+224:offset+240]
        language = lang_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')

        # Create time (4 bytes)
        create_time = struct.unpack('<I', data[offset+240:offset+244])[0]

        # Cover page (2 bytes)
        cover_page = struct.unpack('<H', data[offset+244:offset+246])[0]

        # Chapter count (2 bytes)
        chapter_count = struct.unpack('<H', data[offset+246:offset+248])[0]

        self.metadata = XTCMetadata(
            title=title,
            author=author,
            publisher=publisher,
            language=language,
            create_time=create_time,
            cover_page=cover_page,
            chapter_count=chapter_count
        )

    def _read_chapters(self, data: bytes, offset: int, count: int) -> None:
        """Parse chapter section.

        Args:
            data: Complete file data
            offset: Offset to chapter section
            count: Number of chapters
        """
        for i in range(count):
            chapter_offset = offset + (i * self.CHAPTER_SIZE)

            # Chapter name (80 bytes)
            name_bytes = data[chapter_offset:chapter_offset+80]
            name = name_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')

            # Start page (2 bytes)
            start_page = struct.unpack('<H', data[chapter_offset+80:chapter_offset+82])[0]

            # End page (2 bytes)
            end_page = struct.unpack('<H', data[chapter_offset+82:chapter_offset+84])[0]

            self.chapters.append(XTCChapter(
                name=name,
                start_page=start_page,
                end_page=end_page
            ))

