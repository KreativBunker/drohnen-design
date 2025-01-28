from typing import Optional

import pycountry


class CountryHandler:
    @staticmethod
    def get_country_name(country_code: str) -> Optional[str]:
        country = pycountry.countries.get(alpha_2=country_code)
        return country.name if country else None