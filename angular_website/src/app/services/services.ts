import { HttpClient, HttpHeaders } from "@angular/common/http";
import { Observable } from 'rxjs';
import { Injectable } from "@angular/core";

@Injectable({
  providedIn: 'root'
})
export class ModelService {
    private apiURL = "http://localhost:5000/api/";
    
    constructor(private _http: HttpClient) {}

    getTest(){
        return this._http.get(`${this.apiURL}test/`)
    }

    getStream(): Observable<any>{
        return this._http.get(`${this.apiURL}test/stream/`, {responseType: 'text',
            observe: 'events', reportProgress: true})
    }

    getAgentStream(): Observable<any>{
        return this._http.get(`${this.apiURL}agent/stream/`, {responseType: 'text',
            observe: 'events', reportProgress: true})
    }

    updateQuestion(question: string){
        return this._http.post(`${this.apiURL}question/`, JSON.stringify({"question": question}))
    }

    postCSV(file: any){
        return this._http.post(`${this.apiURL}upload/csv/`, file);
    }
}