import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class Geocodingservice {
  static final String apiKey = dotenv.env['MAP_API_KEY']!;
  static const String baseUrl = "https://graphhopper.com/api/1/geocode";

  static Future<LatLng> getCoordinates(String address) async {
    final url = Uri.parse("$baseUrl?q=$address&limit=18&key=$apiKey");

    final response = await http.get(url);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data["hits"].isNotEmpty) {
        final lat = data["hits"][0]["point"]["lat"];
        final lng = data["hits"][0]["point"]["lng"];
        return LatLng(lat, lng);
      } else {
        throw Exception("No location found");
      }
    } else {
      throw Exception("Geocoding request failed");
    }
  }
}
