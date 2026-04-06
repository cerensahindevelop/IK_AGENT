SCHEMA_METADATA = {
    "personeller": {
        "description": "Çalışanların temel kimlik ve iş bilgilerini tutar.",
        "primary_key": "id",
        "columns": {
            "id": "Personel benzersiz kimliği",
            "ad": "Personelin adı",
            "soyad": "Personelin soyadı",
            "sirket_mail": "Şirket e-posta adresi",
            "tel_no": "Telefon numarası",
            "adres": "İkamet adresi",
            "ise_giris_tarihi": "İşe başlama tarihi",
            "departman_id": "Bağlı olduğu departman kimliği",
            "pozisyon_id": "Bağlı olduğu pozisyon kimliği"
        },
        "foreign_keys": {
            "departman_id": {
                "target_table": "departmanlar",
                "target_column": "id"
            },
            "pozisyon_id": {
                "target_table": "pozisyonlar",
                "target_column": "id"
            }
        },
        "query_hints": {
            "keywords": [
                "personel", "çalışan", "kim", "adı", "soyadı", "mail",
                "telefon", "adres", "işe giriş", "çalışan bilgisi"
            ],
            "common_questions": [
                "Bu personel kimdir?",
                "Ahmet Yılmaz hangi departmanda çalışıyor?",
                "Çalışanın işe giriş tarihi nedir?",
                "Bu kişinin mail adresi nedir?"
            ],
            "frequently_joined_with": [
                "departmanlar", "pozisyonlar", "maaslar",
                "izinler", "devamsizliklar", "performanslar",
                "egitimler", "yan_haklar", "mesailer"
            ]
        }
    },

    "departmanlar": {
        "description": "Şirketteki departman bilgilerini tutar.",
        "primary_key": "id",
        "columns": {
            "id": "Departman benzersiz kimliği",
            "departman_ad": "Departman adı"
        },
        "foreign_keys": {},
        "query_hints": {
            "keywords": [
                "departman", "birim", "hangi departman", "ekip", "bölüm"
            ],
            "common_questions": [
                "Bu personel hangi departmanda çalışıyor?",
                "Şirkette hangi departmanlar var?",
                "Yazılım Geliştirme departmanında kimler çalışıyor?"
            ],
            "frequently_joined_with": [
                "personeller"
            ]
        }
    },

    "pozisyonlar": {
        "description": "Şirketteki pozisyon ve unvan bilgilerini tutar.",
        "primary_key": "id",
        "columns": {
            "id": "Pozisyon benzersiz kimliği",
            "pozisyon_adi": "Pozisyon adı"
        },
        "foreign_keys": {},
        "query_hints": {
            "keywords": [
                "pozisyon", "unvan", "görev", "rol", "meslek"
            ],
            "common_questions": [
                "Bu personelin pozisyonu nedir?",
                "Backend Developer kimdir?",
                "Hangi çalışan hangi pozisyonda?"
            ],
            "frequently_joined_with": [
                "personeller"
            ]
        }
    },

    "maaslar": {
        "description": "Personellerin maaş bilgilerini tutar.",
        "primary_key": "id",
        "columns": {
            "id": "Maaş kaydı benzersiz kimliği",
            "personel_id": "Maaşın ait olduğu personel kimliği",
            "maas": "Maaş tutarı"
        },
        "foreign_keys": {
            "personel_id": {
                "target_table": "personeller",
                "target_column": "id"
            }
        },
        "query_hints": {
            "keywords": [
                "maaş", "ücret", "kazanç", "maaşı ne kadar",
                "en yüksek maaş", "en düşük maaş", "maaş bilgisi"
            ],
            "common_questions": [
                "Ahmet'in maaşı ne kadar?",
                "En yüksek maaşı hangi çalışan alıyor?",
                "50 bin üstü maaş alan personeller kimler?"
            ],
            "frequently_joined_with": [
                "personeller", "departmanlar", "pozisyonlar"
            ]
        }
    },

    "mesailer": {
        "description": "Personellerin fazla mesai kayıtlarını tutar.",
        "primary_key": "id",
        "columns": {
            "id": "Mesai kaydı benzersiz kimliği",
            "personel_id": "Mesainin ait olduğu personel kimliği",
            "tarih": "Mesai tarihi",
            "saat": "Mesai süresi saat cinsinden",
            "mesai_tipi": "Mesai türü"
        },
        "foreign_keys": {
            "personel_id": {
                "target_table": "personeller",
                "target_column": "id"
            }
        },
        "query_hints": {
            "keywords": [
                "mesai", "fazla mesai", "kaç saat mesai",
                "mesai yaptı", "mesai tipi", "hafta sonu mesaisi",
                "gece mesaisi"
            ],
            "common_questions": [
                "Bu personel ne kadar mesai yaptı?",
                "Kim hafta sonu mesaisi yaptı?",
                "Mart ayında en çok mesai yapan personel kim?"
            ],
            "frequently_joined_with": [
                "personeller", "departmanlar", "pozisyonlar"
            ]
        }
    },

    "izinler": {
        "description": "Personellerin onaylı izin kayıtlarını tutar.",
        "primary_key": "id",
        "columns": {
            "id": "İzin kaydı benzersiz kimliği",
            "personel_id": "İznin ait olduğu personel kimliği",
            "baslangic_tarihi": "İzin başlangıç tarihi",
            "bitis_tarihi": "İzin bitiş tarihi",
            "izin_turu": "İzin türü"
        },
        "foreign_keys": {
            "personel_id": {
                "target_table": "personeller",
                "target_column": "id"
            }
        },
        "query_hints": {
            "keywords": [
                "izin", "izinli", "yıllık izin", "hastalık izni",
                "mazeret izni", "hangi tarihler arası izinli",
                "izin kaydı"
            ],
            "common_questions": [
                "Ahmet hangi tarihler arasında izinliydi?",
                "Kimler yıllık izin kullandı?",
                "Mart ayında izinli olan personeller kimler?",
                "Bu kişinin hastalık izni var mı?"
            ],
            "frequently_joined_with": [
                "personeller", "departmanlar", "pozisyonlar"
            ]
        }
    },

    "devamsizliklar": {
        "description": "Personellerin devamsızlık, geç gelme ve erken çıkma kayıtlarını tutar.",
        "primary_key": "id",
        "columns": {
            "id": "Devamsızlık kaydı benzersiz kimliği",
            "id_person": "Kaydın ait olduğu personel kimliği",
            "tarih": "Devamsızlık tarihi",
            "durum": "Devamsızlık durumu"
        },
        "foreign_keys": {
            "id_person": {
                "target_table": "personeller",
                "target_column": "id"
            }
        },
        "query_hints": {
            "keywords": [
                "devamsızlık", "gelmedi", "geç geldi", "erken çıktı",
                "habersiz gelmedi", "disiplin", "yoklama", "devamsızlık durumu"
            ],
            "common_questions": [
                "Bu personelin devamsızlık kaydı var mı?",
                "Kim habersiz gelmedi?",
                "Geç gelen personeller kimler?",
                "Şubat ayında devamsızlık yapanlar kim?"
            ],
            "frequently_joined_with": [
                "personeller", "departmanlar", "pozisyonlar"
            ]
        }
    },

    "performanslar": {
        "description": "Personellerin dönem bazlı performans puanlarını tutar.",
        "primary_key": "id",
        "columns": {
            "id": "Performans kaydı benzersiz kimliği",
            "personel_id": "Performansın ait olduğu personel kimliği",
            "donem": "Değerlendirme dönemi",
            "puan": "Performans puanı"
        },
        "foreign_keys": {
            "personel_id": {
                "target_table": "personeller",
                "target_column": "id"
            }
        },
        "query_hints": {
            "keywords": [
                "performans", "puan", "başarı", "değerlendirme",
                "performans puanı", "en yüksek performans", "dönem puanı"
            ],
            "common_questions": [
                "Bu personelin performans puanı kaç?",
                "2026-Q1 döneminde en yüksek performans kimde?",
                "Performansı 90 üstü olan çalışanlar kimler?"
            ],
            "frequently_joined_with": [
                "personeller", "departmanlar", "pozisyonlar"
            ]
        }
    },

    "egitimler": {
        "description": "Personellerin eğitim kayıtlarını tutar.",
        "primary_key": "id",
        "columns": {
            "id": "Eğitim kaydı benzersiz kimliği",
            "personel_id": "Eğitimin ait olduğu personel kimliği",
            "egitim_adi": "Eğitim adı",
            "egitim_tarihi": "Eğitim tarihi",
            "durum": "Eğitim durumu"
        },
        "foreign_keys": {
            "personel_id": {
                "target_table": "personeller",
                "target_column": "id"
            }
        },
        "query_hints": {
            "keywords": [
                "eğitim", "kurs", "sertifika", "hangi eğitimi aldı",
                "tamamlandı", "devam ediyor", "planlandı", "eğitim durumu"
            ],
            "common_questions": [
                "Bu personel hangi eğitimleri aldı?",
                "Devam eden eğitimler nelerdir?",
                "Kimler Python eğitimi aldı?",
                "Planlanan eğitimler hangileri?"
            ],
            "frequently_joined_with": [
                "personeller", "departmanlar", "pozisyonlar"
            ]
        }
    },

    "yan_haklar": {
        "description": "Personellere tanımlanan yan hakları tutar.",
        "primary_key": "id",
        "columns": {
            "id": "Yan hak kaydı benzersiz kimliği",
            "personel_id": "Yan hakkın ait olduğu personel kimliği",
            "hak_adi": "Yan hak adı",
            "durum": "Yan hak durumu",
            "tanimlanma_tarihi": "Yan hakkın tanımlandığı tarih"
        },
        "foreign_keys": {
            "personel_id": {
                "target_table": "personeller",
                "target_column": "id"
            }
        },
        "query_hints": {
            "keywords": [
                "yan hak", "hak", "yemek kartı", "özel sağlık sigortası",
                "servis", "internet desteği", "prim desteği",
                "uzaktan çalışma desteği"
            ],
            "common_questions": [
                "Bu personelin yan hakları nelerdir?",
                "Kimde özel sağlık sigortası var?",
                "Aktif yan hakları olan personeller kimler?",
                "Servis hakkı pasif olan çalışanlar kim?"
            ],
            "frequently_joined_with": [
                "personeller", "departmanlar", "pozisyonlar"
            ]
        }
    }
}
    