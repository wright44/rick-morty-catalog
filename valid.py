"""
Rick and Morty Character Catalog - Business Logic Layer
Повна реалізація бізнес-логіки в одному файлі
"""

import json
import requests
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime
from collections import Counter


# ==================== ENUMS ====================

class CharacterStatus(Enum):
    """Статус персонажа."""
    ALIVE = "Alive"
    DEAD = "Dead"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, value: str) -> 'CharacterStatus':
        for status in cls:
            if status.value.lower() == value.lower().strip():
                return status
        return cls.UNKNOWN


class Gender(Enum):
    """Стать персонажа."""
    MALE = "Male"
    FEMALE = "Female"
    GENDERLESS = "Genderless"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, value: str) -> 'Gender':
        for gender in cls:
            if gender.value.lower() == value.lower().strip():
                return gender
        return cls.UNKNOWN


class Species(Enum):
    """Вид персонажа."""
    HUMAN = "Human"
    ALIEN = "Alien"
    HUMANOID = "Humanoid"
    ROBOT = "Robot"
    ANIMAL = "Animal"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, value: str) -> 'Species':
        for species in cls:
            if species.value.lower() == value.lower().strip():
                return species
        return cls.UNKNOWN


class SortField(Enum):
    """Поля для сортування."""
    ID = "id"
    NAME = "name"
    STATUS = "status"
    EPISODES = "episodes"


class SortOrder(Enum):
    """Напрямок сортування."""
    ASC = "asc"
    DESC = "desc"


# ==================== DOMAIN MODELS ====================

@dataclass
class Location:
    """Локація персонажа."""
    name: str
    url: str = ""
    
    @property
    def id(self) -> Optional[int]:
        if self.url:
            try:
                return int(self.url.rstrip('/').split('/')[-1])
            except (ValueError, IndexError):
                return None
        return None


@dataclass
class Character:
    """Модель персонажа."""
    id: int
    name: str
    status: CharacterStatus
    species: Species
    type: str
    gender: Gender
    origin: Location
    location: Location
    image_url: str
    episode_ids: List[int] = field(default_factory=list)
    url: str = ""
    created: Optional[datetime] = None
    
    @property
    def episode_count(self) -> int:
        return len(self.episode_ids)
    
    @property
    def is_alive(self) -> bool:
        return self.status == CharacterStatus.ALIVE
    
    @property
    def status_emoji(self) -> str:
        return {"Alive": "🟢", "Dead": "🔴", "unknown": "⚪"}.get(self.status.value, "⚪")
    
    @property
    def display_species(self) -> str:
        return f"{self.species.value} ({self.type})" if self.type else self.species.value
    
    def __str__(self) -> str:
        return f"{self.status_emoji} {self.name} - {self.display_species}"


# ==================== JSON PARSER ====================

class JsonParseError(Exception):
    """Помилка парсингу JSON."""
    pass


class CharacterParser:
    """Парсер JSON-даних персонажів."""
    
    @staticmethod
    def _extract_ids_from_urls(urls: List[str]) -> List[int]:
        """Витягує ID з URL."""
        ids = []
        for url in urls:
            try:
                ids.append(int(url.rstrip('/').split('/')[-1]))
            except (ValueError, IndexError, AttributeError):
                continue
        return ids
    
    @staticmethod
    def _parse_location(data: Dict[str, Any]) -> Location:
        """Парсить локацію."""
        return Location(
            name=data.get('name', 'Unknown'),
            url=data.get('url', '')
        )
    
    @staticmethod
    def _parse_datetime(date_string: str) -> Optional[datetime]:
        """Парсить дату."""
        if not date_string:
            return None
        try:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    @classmethod
    def parse_character(cls, data: Dict[str, Any]) -> Character:
        """Парсить одного персонажа."""
        if 'id' not in data or 'name' not in data:
            raise JsonParseError(f"Missing required fields: {data}")
        
        return Character(
            id=data['id'],
            name=data['name'],
            status=CharacterStatus.from_string(data.get('status', 'unknown')),
            species=Species.from_string(data.get('species', 'unknown')),
            type=data.get('type', ''),
            gender=Gender.from_string(data.get('gender', 'unknown')),
            origin=cls._parse_location(data.get('origin', {})),
            location=cls._parse_location(data.get('location', {})),
            image_url=data.get('image', ''),
            episode_ids=cls._extract_ids_from_urls(data.get('episode', [])),
            url=data.get('url', ''),
            created=cls._parse_datetime(data.get('created', ''))
        )
    
    @classmethod
    def parse_character_list(cls, data: Dict[str, Any]) -> Tuple[List[Character], Dict[str, Any]]:
        """Парсить список персонажів."""
        info = data.get('info', {})
        pagination = {
            'count': info.get('count', 0),
            'pages': info.get('pages', 0),
            'next': info.get('next'),
            'prev': info.get('prev')
        }
        
        characters = []
        for char_data in data.get('results', []):
            try:
                characters.append(cls.parse_character(char_data))
            except JsonParseError as e:
                print(f"Warning: {e}")
        
        return characters, pagination


# ==================== FILTER ENGINE ====================

@dataclass
class FilterCriteria:
    """Критерії фільтрації."""
    name: Optional[str] = None
    status: Optional[CharacterStatus] = None
    species: Optional[Species] = None
    gender: Optional[Gender] = None
    min_episodes: Optional[int] = None
    max_episodes: Optional[int] = None
    
    def is_empty(self) -> bool:
        return all(v is None for v in [
            self.name, self.status, self.species, 
            self.gender, self.min_episodes, self.max_episodes
        ])
    
    def to_api_params(self) -> dict:
        params = {}
        if self.name:
            params['name'] = self.name
        if self.status:
            params['status'] = self.status.value
        if self.species:
            params['species'] = self.species.value
        if self.gender:
            params['gender'] = self.gender.value
        return params


@dataclass
class SortCriteria:
    """Критерії сортування."""
    field: SortField = SortField.ID
    order: SortOrder = SortOrder.ASC


class FilterEngine:
    """Механізм фільтрації та сортування."""
    
    @staticmethod
    def filter_characters(characters: List[Character], criteria: FilterCriteria) -> List[Character]:
        """Фільтрує персонажів."""
        if criteria.is_empty():
            return characters
        
        result = characters.copy()
        
        if criteria.name:
            result = [c for c in result if criteria.name.lower() in c.name.lower()]
        if criteria.status:
            result = [c for c in result if c.status == criteria.status]
        if criteria.species:
            result = [c for c in result if c.species == criteria.species]
        if criteria.gender:
            result = [c for c in result if c.gender == criteria.gender]
        if criteria.min_episodes is not None:
            result = [c for c in result if c.episode_count >= criteria.min_episodes]
        if criteria.max_episodes is not None:
            result = [c for c in result if c.episode_count <= criteria.max_episodes]
        
        return result
    
    @staticmethod
    def sort_characters(characters: List[Character], criteria: SortCriteria) -> List[Character]:
        """Сортує персонажів."""
        key_map = {
            SortField.ID: lambda c: c.id,
            SortField.NAME: lambda c: c.name.lower(),
            SortField.STATUS: lambda c: c.status.value,
            SortField.EPISODES: lambda c: c.episode_count
        }
        
        key_func = key_map.get(criteria.field, lambda c: c.id)
        reverse = criteria.order == SortOrder.DESC
        
        return sorted(characters, key=key_func, reverse=reverse)


# ==================== VALIDATORS ====================

@dataclass
class ValidationError:
    """Помилка валідації."""
    field: str
    message: str


@dataclass
class ValidationResult:
    """Результат валідації."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)


class CharacterValidator:
    """Валідатор персонажів."""
    
    @staticmethod
    def validate(character: Character) -> ValidationResult:
        errors = []
        
        if character.id <= 0:
            errors.append(ValidationError("id", "ID must be positive"))
        
        if not character.name or not character.name.strip():
            errors.append(ValidationError("name", "Name cannot be empty"))
        
        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        return ValidationResult(is_valid=True)


# ==================== STATISTICS SERVICE ====================

@dataclass
class CatalogStatistics:
    """Статистика каталогу."""
    total_characters: int
    status_distribution: Dict[str, int]
    species_distribution: Dict[str, int]
    gender_distribution: Dict[str, int]
    avg_episodes: float
    top_characters: List[Tuple[str, int]]


class StatisticsService:
    """Сервіс статистики."""
    
    @staticmethod
    def calculate(characters: List[Character]) -> CatalogStatistics:
        if not characters:
            return CatalogStatistics(0, {}, {}, {}, 0.0, [])
        
        status_counter = Counter(c.status.value for c in characters)
        species_counter = Counter(c.species.value for c in characters)
        gender_counter = Counter(c.gender.value for c in characters)
        
        avg_eps = sum(c.episode_count for c in characters) / len(characters)
        
        top = sorted(characters, key=lambda c: c.episode_count, reverse=True)[:5]
        top_chars = [(c.name, c.episode_count) for c in top]
        
        return CatalogStatistics(
            total_characters=len(characters),
            status_distribution=dict(status_counter),
            species_distribution=dict(species_counter),
            gender_distribution=dict(gender_counter),
            avg_episodes=round(avg_eps, 2),
            top_characters=top_chars
        )
    
    @staticmethod
    def format_report(stats: CatalogStatistics) -> str:
        lines = [
            "=" * 50,
            "CATALOG STATISTICS",
            "=" * 50,
            f"Total: {stats.total_characters}",
            "",
            "Status:",
            *[f"  {k}: {v}" for k, v in stats.status_distribution.items()],
            "",
            "Top Species:",
            *[f"  {k}: {v}" for k, v in list(stats.species_distribution.items())[:5]],
            "",
            f"Avg Episodes: {stats.avg_episodes}",
            "",
            "Most Appearing:",
            *[f"  {name}: {eps} eps" for name, eps in stats.top_characters],
            "=" * 50
        ]
        return "\n".join(lines)


# ==================== VIEW MODELS ====================

@dataclass
class CharacterCardVM:
    """ViewModel для картки персонажа."""
    id: int
    name: str
    status_text: str
    status_emoji: str
    status_color: str
    species_text: str
    location_text: str
    episodes_text: str
    image_url: str
    
    @classmethod
    def from_character(cls, c: Character) -> 'CharacterCardVM':
        colors = {"Alive": "#4CAF50", "Dead": "#f44336", "unknown": "#9E9E9E"}
        return cls(
            id=c.id,
            name=c.name,
            status_text=c.status.value,
            status_emoji=c.status_emoji,
            status_color=colors.get(c.status.value, "#9E9E9E"),
            species_text=c.display_species,
            location_text=f"📍 {c.location.name}",
            episodes_text=f"🎬 {c.episode_count} episodes",
            image_url=c.image_url
        )


# ==================== CATALOG SERVICE ====================

@dataclass
class PageInfo:
    """Інформація про сторінку."""
    current: int
    total: int
    count: int
    has_next: bool
    has_prev: bool


@dataclass
class CatalogResult:
    """Результат запиту."""
    characters: List[Character]
    page_info: PageInfo


class CatalogService:
    """Головний сервіс каталогу."""
    
    BASE_URL = "https://rickandmortyapi.com/api"
    
    def __init__(self):
        self._cache: Dict[int, Character] = {}
        self._parser = CharacterParser()
        self._filter = FilterEngine()
    
    def get_page(self, page: int = 1, filters: Optional[FilterCriteria] = None) -> CatalogResult:
        """Отримує сторінку персонажів."""
        params = {'page': page}
        if filters:
            params.update(filters.to_api_params())
        
        try:
            response = requests.get(f"{self.BASE_URL}/character", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"API Error: {e}")
            return CatalogResult([], PageInfo(1, 1, 0, False, False))
        
        characters, pagination = self._parser.parse_character_list(data)
        
        # Кешуємо
        for c in characters:
            self._cache[c.id] = c
        
        # Локальна фільтрація (для полів, які не підтримує API)
        if filters and (filters.min_episodes or filters.max_episodes):
            characters = self._filter.filter_characters(characters, filters)
        
        page_info = PageInfo(
            current=page,
            total=pagination.get('pages', 1),
            count=pagination.get('count', len(characters)),
            has_next=pagination.get('next') is not None,
            has_prev=pagination.get('prev') is not None
        )
        
        return CatalogResult(characters, page_info)
    
    def get_by_id(self, character_id: int) -> Optional[Character]:
        """Отримує персонажа за ID."""
        if character_id in self._cache:
            return self._cache[character_id]
        
        try:
            response = requests.get(f"{self.BASE_URL}/character/{character_id}", timeout=10)
            response.raise_for_status()
            character = self._parser.parse_character(response.json())
            self._cache[character_id] = character
            return character
        except (requests.RequestException, JsonParseError):
            return None
    
    def search(self, query: str) -> List[Character]:
        """Пошук персонажів."""
        result = self.get_page(1, FilterCriteria(name=query))
        return result.characters
    
    def get_statistics(self, characters: Optional[List[Character]] = None) -> CatalogStatistics:
        """Отримує статистику."""
        if characters is None:
            result = self.get_page(1)
            characters = result.characters
        return StatisticsService.calculate(characters)


# ==================== DEMO ====================

def main():
    """Демонстрація роботи бізнес-логіки."""
    print("=" * 60)
    print("Rick and Morty Character Catalog - Business Logic Demo")
    print("=" * 60)
    print()
    
    # Ініціалізація сервісу
    catalog = CatalogService()
    
    # 1. Отримання першої сторінки
    print("1. Завантаження персонажів...")
    result = catalog.get_page(1)
    print(f"   Завантажено: {len(result.characters)} персонажів")
    print(f"   Сторінка: {result.page_info.current}/{result.page_info.total}")
    print(f"   Всього: {result.page_info.count}")
    print()
    
    # 2. Виведення перших 5 персонажів
    print("2. Перші 5 персонажів:")
    for c in result.characters[:5]:
        print(f"   {c}")
    print()
    
    # 3. Фільтрація
    print("3. Фільтрація (живі люди):")
    filters = FilterCriteria(status=CharacterStatus.ALIVE, species=Species.HUMAN)
    filtered = catalog.get_page(1, filters)
    print(f"   Знайдено: {len(filtered.characters)}")
    for c in filtered.characters[:3]:
        print(f"   {c}")
    print()
    
    # 4. Пошук
    print("4. Пошук 'Rick':")
    search_results = catalog.search("Rick")
    print(f"   Знайдено: {len(search_results)}")
    for c in search_results[:3]:
        print(f"   {c}")
    print()
    
    # 5. Сортування
    print("5. Сортування за епізодами (DESC):")
    sort = SortCriteria(SortField.EPISODES, SortOrder.DESC)
    sorted_chars = FilterEngine.sort_characters(result.characters, sort)
    for c in sorted_chars[:5]:
        print(f"   {c.name}: {c.episode_count} episodes")
    print()
    
    # 6. Статистика
    print("6. Статистика:")
    stats = catalog.get_statistics(result.characters)
    print(StatisticsService.format_report(stats))
    print()
    
    # 7. ViewModels
    print("7. ViewModels для UI:")
    for c in result.characters[:3]:
        vm = CharacterCardVM.from_character(c)
        print(f"   {vm.status_emoji} {vm.name}")
        print(f"      {vm.species_text}")
        print(f"      {vm.location_text}")
        print(f"      {vm.episodes_text}")
    print()
    
    # 8. Валідація
    print("8. Валідація:")
    for c in result.characters[:2]:
        validation = CharacterValidator.validate(c)
        status = "✓ Valid" if validation.is_valid else f"✗ Invalid: {validation.errors}"
        print(f"   {c.name}: {status}")
    
    print()
    print("=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
