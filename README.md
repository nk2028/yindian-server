# Server of Yindian

## Introduction

Yindian (漢字音典, Chinese Dialect Pronunciation Atlas) is a comprehensive collection of Chinese character pronunciations across various Chinese dialects. It originated from the MCPDict created by Maigo at [MCPDict](https://github.com/MaigoAkisame/MCPDict). Since then, many experts have joined forces to continually collect and organize a large amount of Chinese dialect pronunciation data, resulting in the creation of the Chinese Dialect Pronunciation Atlas project. However, due to a lack of maintenance on the Chinese Dialect Pronunciation Atlas App, nk2028 took over the project and released the web version.

## Design

The design of Yindian is divided into three parts: data source, frontend, and backend. The data is located at [osfans/MCPDict](https://github.com/osfans/MCPDict), the frontend is at [nk2028/hdqt](https://github.com/nk2028/hdqt), and this repository is the backend. The data source is the original MCPDict project, and the main part of this project is the Dockerfile. During the building of the Docker image, the MCPDict's build script is executed, and then the backend server is started to provide APIs for use by the frontend. The server is deployed on Google Cloud Run.

---

# 漢字音典伺服器

## 簡介

漢字音典（Yindian）是全面收集各種漢語方言中漢字讀音的資料庫。它源自 Maigo 製作的 [MCPDict](https://github.com/MaigoAkisame/MCPDict)。此後，由眾多專家聯手，不斷收集整理大量漢語方言讀音資料，製作了漢字音典專案。然而，由於漢字音典 App 缺乏維護，nk2028 接管了這一專案，並發佈了網頁版。

## 設計

HDQT 的設計分為數據源、前端和後端三部分，數據位於 [osfans/MCPDict](https://github.com/osfans/MCPDict)，前端位於 [nk2028/hdqt](https://github.com/nk2028/hdqt)，而本倉庫是後端。數據源即原始的 MCPDict 專案，本專案的主要部分為 Dockerfile，在 Docker 鏡像構建時執行 MCPDict 的構建腳本，然後啓動後端伺服器提供 API，供前端使用。伺服器部署於騰訊雲。

---

Develop:

```
docker build -t yindian-server .
docker tag yindian-server:latest ccr.ccs.tencentyun.com/nk2028/yindian-server:latest
docker push ccr.ccs.tencentyun.com/nk2028/yindian-server:latest
```

