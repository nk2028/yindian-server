# Server of Yindian Web App

Yindian (Chinese Character Pronunciation Dictionary) is a comprehensive database of Chinese character pronunciations. It originated from [MCPDict](https://github.com/MaigoAkisame/MCPDict) created by Maigo and is one of the earliest tools for querying Chinese character readings. Subsequently, numerous experts collaborated to continuously collect and organise a vast amount of pronunciation data, resulting in the [Yindian mobile app](https://github.com/osfans/MCPDict). Based on the Yindian app, nk2028 released Yindian Web, enabling more users to conveniently query character pronunciations across different historical periods and geographical regions. At present, Yindian Web includes over a thousand language varieties, covering Old Chinese, Middle Chinese, Early Modern Chinese, and modern dialects.

The Yindian Web App is divided into three major components: the data source, the frontend, and the backend. The data is stored in [osfans/MCPDict](https://github.com/osfans/MCPDict); the frontend is maintained under [nk2028/yindian](https://github.com/nk2028/yindian); and this repository comprises the backend.

The backend itself is organised into two primary directories. The `build/` directory contains a build script that generates a `mcpdict.db` file within the `server/` directory. The `server/` directory contains a `Dockerfile` and a server script, which are used to construct the Docker image, making it suitable for deployment in server environments.

The backend is deployed on Tencent Cloud's Serverless Cloud Function (SCF) platform.

To build the backend, please refer to `.github/workflows/deploy.yml`.

---

# 音典網頁版伺服器

漢字音典是全面收集漢字讀音的資料庫。它源自 Maigo 製作的 [MCPDict](https://github.com/MaigoAkisame/MCPDict)，是最早的漢字讀音查詢工具之一。此後，由眾多專家聯手，不斷收集整理大量漢字讀音資料，製作了[漢字音典 APP](https://github.com/osfans/MCPDict)。nk2028 基於漢字音典 APP 發佈了音典網頁版，讓更多使用者能夠方便地查詢漢字在不同時代、不同地區的讀音。目前音典網頁版收錄了千餘種語言變體，涵蓋上古音、中古音、近代音及現代方言。

音典網頁版的設計分為數據源、前端和後端三部分，數據源是 [osfans/MCPDict](https://github.com/osfans/MCPDict)，前端是 [nk2028/yindian](https://github.com/nk2028/yindian)，而本倉庫是後端。

後端主要分為兩部分。`build/` 目錄中存放構建腳本，執行後在 `server/` 目錄下生成 `mcpdict.db` 檔案；而 `server/` 目錄下包含 `Dockerfile` 與伺服器腳本，可構建 Docker 鏡像，適合在伺服器上部署。

音典網頁版的後端部署於騰訊雲雲函數 SCF。

構建命令請參考 `.github/workflows/deploy.yml`.

---

# API Description

### 1\. `GET /list-langs/`

Query Parameters: None

Example Response:

```js
{
    "version": "1770216365",
    "data": [
        [
            2312, // 語言ID
            "興寧話", // 語言
            "興寧", // 簡稱
            "HFB-006", // 地圖集二排序
            "#A5C24E", // 地圖集二顏色
            "客家話－粤臺片－龍華小片", // 地圖集二分區
            "L7A-107", // 音典排序
            "#BFB465", // 音典顏色
            "閩－閩西－嘉應", // 音典分區
            "33B3", // 陳邡排序
            "#008000", // 陳邡顏色
            "客家－嘉應－嘉應片", // 陳邡分區
            "廣東梅州興寧興城", // 地點
            "115.735283,24.136753" // 經緯度
        ],
        ...
    ]
```

### 2\. `GET /chars/`

Query Parameters:

| Name | Type | Description | Required |
| :- | :- | :- | :- |
| `chars` | `str` | A string of Chinese characters, e.g. `"是社"` | Yes |

Example Response:

```js
{
  "version": "1770216365",
  "data": [
    ["語言ID", "意", "思", "是"], // header
    [
      222,
      "i5",
      "", // missing values
      ""
    ],
    [
      2215,
      "i5",
      [["so5"], ["so1"]],  // multiple readings
      "si5"
    ]，
    [
      2312,
      "ʒɪ5",
      "sɿ1",
      "ʃɪ5"
    ],
    [
      2325,
      "i5",
      [["sɿ1", "*思*想,*思*念"], ["sɿ5", "意*思*"]], // multiple readings with annotations
      "sɿ5"
    ]
  ]
}
```
